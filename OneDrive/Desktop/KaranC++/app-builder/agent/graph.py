from dotenv import load_dotenv
from langchain.globals import set_verbose, set_debug
from langchain_groq.chat_models import ChatGroq
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import *
from agent.states import *
from agent.tools import (write_file, write_file_no_prefix,
                        read_file, read_file_no_prefix,
                        get_current_directory, get_current_directory_no_prefix,
                        list_file, list_file_no_prefix,
                        print_tree, print_tree_no_prefix,
                        open_file, open_file_no_prefix)

_ = load_dotenv()

set_debug(True)
set_verbose(True)

llm = ChatGroq(model="openai/gpt-oss-120b")

def planner_agent(state: dict) -> dict:
    """Converts user prompt into a structured Plan."""
    user_prompt = state["user_prompt"]
    resp = llm.with_structured_output(Plan).invoke(
        planner_prompt(user_prompt)
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    """Creates TaskPlan from Plan."""
    plan: Plan = state["plan"]
    resp = llm.with_structured_output(TaskPlan).invoke(
        architect_prompt(plan=plan.model_dump_json())
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")

    resp.plan = plan
    print(resp.model_dump_json())
    return {"task_plan": resp}


def coder_agent(state: dict) -> dict:
    """LangGraph tool-using coder agent."""
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    existing_content = read_file.run(current_task.filepath)

    system_prompt = coder_system_prompt()
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
        "Use write_file(path, content) to save your changes."
    )

    coder_tools = [
        read_file, read_file_no_prefix,
        write_file, write_file_no_prefix,
        list_file, list_file_no_prefix,
        get_current_directory, get_current_directory_no_prefix,
        print_tree, print_tree_no_prefix,
        open_file, open_file_no_prefix
    ]
    react_agent = create_react_agent(llm, coder_tools)

    # CRITICAL: Add retry logic to handle model failures
    max_retries = 3
    success = False

    for attempt in range(max_retries):
        try:
            react_agent.invoke({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            })
            success = True
            break  # Success - exit retry loop

        except Exception as e:
            error_msg = str(e)
            print(f"\n⚠️  Attempt {attempt + 1}/{max_retries} failed")
            print(f"Error: {error_msg[:150]}...")

            if attempt < max_retries - 1:
                print("🔄 Retrying with simplified prompt...")
                # Simplify the prompt for retry
                user_prompt = (
                    f"Create file: {current_task.filepath}\n"
                    f"Task: {current_task.task_description}\n"
                    "IMPORTANT: Call write_file with ONLY path and content parameters. No other parameters."
                )
            else:
                print(f"❌ Failed after {max_retries} attempts. Skipping this step.")
                # Try to write a basic file directly as fallback
                try:
                    basic_content = f"// TODO: Implement {current_task.task_description}\n"
                    write_file.invoke({"path": current_task.filepath, "content": basic_content})
                    print(f"✅ Created placeholder file: {current_task.filepath}")
                except:
                    print(f"⚠️  Could not create placeholder file")

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


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
    result = agent.invoke({"user_prompt": "Build a colourful modern todo app in html css and js"},
                          {"recursion_limit": 100})
    print("Final State:", result)

#Build a colourful modern todo app in html css and js
