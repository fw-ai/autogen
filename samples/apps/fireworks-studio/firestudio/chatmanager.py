from copy import deepcopy
import json
import time
from typing import Any, Dict, List
from .datamodel import AgentWorkFlowConfig, Message
from .utils import (
    extract_successful_code_blocks,
    get_default_agent_config,
    get_modified_files,
)
from .workflowmanager import AutoGenWorkFlowManager
import os


class AutoGenChatManager:
    def __init__(self) -> None:
        pass

    def chat(
        self,
        message: Message,
        history_list: List[Message],
        agent_flow_config: AgentWorkFlowConfig = None,
        **kwargs,
    ) -> Dict[str, Message]:
        _work_dir_prefix = kwargs.get("work_dir", None)
        output_message: List[Message] = []

        parent_flow_config = deepcopy(agent_flow_config)
        if not isinstance(parent_flow_config.receiver, list):
            parent_flow_config.receiver = [parent_flow_config.receiver]

        for idx in range(len(parent_flow_config.receiver)):
            if parent_flow_config is None:
                flow_config = None
            else:
                flow_config = deepcopy(parent_flow_config)
                flow_config.receiver = flow_config.receiver[idx]

            # if no flow config is provided, use the default
            if flow_config is None:
                flow_config = get_default_agent_config(scratch_dir)

            work_dir = os.path.join(_work_dir_prefix, f"{str(idx)}")
            scratch_dir = os.path.join(work_dir, "scratch")
            os.makedirs(scratch_dir, exist_ok=True)
            receiver_name = flow_config.receiver.config.name
            history = [
                message
                for message in history_list
                if message.receiver_name == receiver_name
            ]

            flow = AutoGenWorkFlowManager(
                config=flow_config, history=history, work_dir=scratch_dir
            )
            message_text = message.content.strip()

            output = ""
            start_time = time.time()

            metadata = {}
            flow.run(message=f"{message_text}", clear_history=False)

            metadata["messages"] = flow.agent_history

            output = ""

            if flow_config.summary_method == "last":
                successful_code_blocks = extract_successful_code_blocks(
                    flow.agent_history
                )
                last_message = flow.agent_history[-1]["message"]["content"]
                successful_code_blocks = "\n\n".join(successful_code_blocks)
                output = (
                    (last_message + "\n" + successful_code_blocks)
                    if successful_code_blocks
                    else last_message
                )
            elif flow_config.summary_method == "llm":
                output = ""
            elif flow_config.summary_method == "none":
                output = ""

            metadata["code"] = ""
            end_time = time.time()
            metadata["time"] = end_time - start_time
            modified_files = get_modified_files(
                start_time, end_time, scratch_dir, dest_dir=work_dir
            )
            metadata["files"] = modified_files

            print("Modified files: ", len(modified_files))

            output_message.append(
                Message(
                    user_id=message.user_id,
                    root_msg_id=message.root_msg_id,
                    role="assistant",
                    content=output,
                    receiver_name=receiver_name,
                    metadata=json.dumps(metadata),
                    session_id=message.session_id,
                )
            )

        return output_message
