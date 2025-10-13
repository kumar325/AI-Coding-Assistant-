#Call LLM and create graph for agents

#imported this to get AI debugger to work, may not need  for final
import sys
import os
from gc import set_debug

# Add the agent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()
from langchain.globals import set_verbose, set_debug
from langchain_groq.chat_models import ChatGroq
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import *
from agent.states import *
from agent.tools import *

set_debug(True)
set_verbose(True)

llm = ChatGroq(model="openai/gpt-oss-120b")

#takes the state dictionary as input, returns dictionary of output
def planner_agent(state: dict) -> dict:
    user_prompt = state["user_prompt"]
    resp = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    return {"plan": resp}

#takes input of planner_agent function, returns the implementation steps
def architect_agent(state: dict) -> dict:
    plan: Plan = state["plan"]
    resp = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan))
    if resp is None:
        raise ValueError("Architect did not return a valid response.")

    resp.plan = plan

    return {"task_plan": resp}

# writes code based on each of the implementation steps
# CHANGED THIS
def coder_agent(state: dict) -> dict:
    coder_state = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]

    # Initialize project root
    init_project_root()

    # Read existing file content
    existing_content = read_file.invoke({"path": current_task.filepath})

    # Create detailed prompt for the coder
    user_prompt = f"""
Task: {current_task.task_description}

File to work on: {current_task.filepath}

Existing content:
{existing_content if existing_content else "[File is empty or doesn't exist yet]"}

Instructions:
1. Use write_file(path, content) to create or update the file
2. Use read_file(path) to check existing files
3. Use list_files(directory) to see what files exist
4. Write complete, working code - no placeholders or TODOs
5. Include all necessary imports and error handling

After writing the file, confirm completion.
"""

    system_prompt = coder_system_prompt()

    # Define tools for the agent - make sure these match your @tool decorators
    coder_tools = [write_file, read_file, list_files, get_current_directory]

    # Create React agent with strict tool validation
    react_agent = create_react_agent(llm, coder_tools)

    try:
        # Invoke the React agent
        result = react_agent.invoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        })

        # Log the result for debugging
        print(f"✅ Completed task {coder_state.current_step_idx + 1}/{len(steps)}")
        print(f"   File: {current_task.filepath}")

    except Exception as e:
        print(f"Error in coder agent: {e}")
        # Continue to next task even if this one fails
        pass

    # Move to next task
    coder_state.current_step_idx += 1

    return {"coder_state": coder_state}


#work flow
graph = StateGraph(dict)
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

graph.set_entry_point("planner")

agent = graph.compile()

if __name__ == "__main__":
    user_prompt = "create a simple calculator web application"

    result = agent.invoke({"user_prompt": user_prompt},
                          {"recursion_limit": 100})
    print(result)
