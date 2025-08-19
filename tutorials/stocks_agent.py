from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition


from langchain.chat_models import init_chat_model

from dotenv import load_dotenv



load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]

#creating tools
@tool
def get_stock_price(symbol:str) -> float:
    ''' Return the current prince of the stock given the stock symbol.'''
    return {'MARUTI': 14090.00,
        'HEROMOTOCO': 4990.00,
        'NESTLEIND': 1146.40,
        'BAJFINANCE': 905.05,
        'BAJAJ-AUTO': 8592.00
            }.get(symbol,0.0)

@tool
def buy_stock(symbol:str, quantity: int, total_price: float) -> str:
    ''' buy the stock given the stock symbol and quantity. '''

    decision = interrupt(f"approve buying {symbol} {quantity} stocks for ${total_price:.2f}")

    if decision == "yes":
        return f"you bought the {quantity} of {symbol} stocks for a {total_price:.2f} "
    else:
        return "buying declined"
#initializing the tools into a list
tools = [get_stock_price, buy_stock]

#initializing the llm with tools
llm = init_chat_model("google_genai:gemini-2.0-flash")
llm_with_tools = llm.bind_tools(tools)

#creating the nodes to be used for graph
def chatbot_agent(state:State):
    msg = llm_with_tools.invoke(state["messages"])
    return {"messages":[msg]}

#initializing the memory
memory = MemorySaver()

#initializing the graph
builder = StateGraph(State)

#adding the nodes to graph
builder.add_node("chatbot_agent_node", chatbot_agent)
builder.add_node("tools", ToolNode(tools))

#bridging the nodes with edges
builder.add_edge(START, "chatbot_agent_node")
builder.add_conditional_edges("chatbot_agent_node", tools_condition)
builder.add_edge("tools", "chatbot_agent_node")
builder.add_edge("chatbot_agent_node",END)

#compile the graph
graph = builder.compile(checkpointer = memory)

config = {"configurable":{"thread_id":"buy_thread"}}

#step1: user asks price
state = graph.invoke({"messages":[{"role":"user","content":"what is the current 10 MARUTI stocks price ?"}]}, config = config)
print(state["messages"][-1].content)

#step2: user asks to buy
state = graph.invoke({"messages":[{"role":"user","content":"Buy the MARUTI stocks 10 in quantity at current price"}]}, config = config)
print(state.get("__interrupt__"))

decision = input("give your approval by typing yes or no :")
state = graph.invoke(Command(resume = decision), config = config)
print(state["messages"][-1].content)




