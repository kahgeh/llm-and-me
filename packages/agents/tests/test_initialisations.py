import tempfile
import unittest
from pathlib import Path

from llm_and_me_agents.initialisations import load_agent_specifications
from llm_and_me_agents.models import AgentSpecification


class TestAgentSpecificationLoading(unittest.TestCase):
    def test_load_agent_specifications_successfully(self):
        sample_toml_content = """
[[agents]]
name = "Test Agent 1"
description = "A test agent."
llm_model_name = "test-model-1"
data_classification = "public"
mcp_servers = ["server1", "server2"]
instructions = "Instructions for Test Agent 1."

[[agents]]
name = "Test Agent 2"
description = "Another test agent."
llm_model_name = "test-model-2"
base_url = "http://localhost:1234/v1"
data_classification = "internal-only"
mcp_servers = ["server3"]
instructions = "Instructions for Test Agent 2. Be very specific."
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as tmp_file:
            tmp_file.write(sample_toml_content)
            tmp_file_path = tmp_file.name

        try:
            specs = load_agent_specifications(file_path=tmp_file_path)

            self.assertEqual(len(specs), 2)

            # Verify first agent
            spec1 = specs[0]
            self.assertIsInstance(spec1, AgentSpecification)
            self.assertEqual(spec1.name, "Test Agent 1")
            self.assertEqual(spec1.description, "A test agent.")
            self.assertEqual(spec1.llm_model_name, "test-model-1")
            self.assertIsNone(spec1.base_url)
            self.assertEqual(spec1.data_classification, "public")
            self.assertEqual(spec1.mcp_servers, ["server1", "server2"])
            self.assertEqual(spec1.instructions, "Instructions for Test Agent 1.")

            # Verify second agent
            spec2 = specs[1]
            self.assertIsInstance(spec2, AgentSpecification)
            self.assertEqual(spec2.name, "Test Agent 2")
            self.assertEqual(spec2.description, "Another test agent.")
            self.assertEqual(spec2.llm_model_name, "test-model-2")
            self.assertEqual(spec2.base_url, "http://localhost:1234/v1")
            self.assertEqual(spec2.data_classification, "internal-only")
            self.assertEqual(spec2.mcp_servers, ["server3"])
            self.assertEqual(spec2.instructions, "Instructions for Test Agent 2. Be very specific.")

        finally:
            Path(tmp_file_path).unlink() # Clean up the temporary file

    def test_load_agent_specifications_file_not_found(self):
        with self.assertRaises(SystemExit) as cm:
            load_agent_specifications(file_path="non_existent_file.toml")
        self.assertEqual(cm.exception.code, 1)

    def test_load_agent_specifications_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as tmp_file:
            tmp_file.write("") # Empty content
            tmp_file_path = tmp_file.name
        
        try:
            # Depending on strictness, this might raise an error or return empty list.
            # The current implementation prints a warning and returns an empty list.
            specs = load_agent_specifications(file_path=tmp_file_path)
            self.assertEqual(len(specs), 0)
        finally:
            Path(tmp_file_path).unlink()

    def test_load_agent_specifications_malformed_toml(self):
        sample_toml_content = """
[[agents]]
name = "Test Agent 1"
description = "A test agent."
llm_model_name = 
data_classification = "public" # Missing value for llm_model_name
mcp_servers = ["server1", "server2"]
instructions = "Instructions for Test Agent 1."
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as tmp_file:
            tmp_file.write(sample_toml_content)
            tmp_file_path = tmp_file.name

        try:
            with self.assertRaises(SystemExit) as cm:
                load_agent_specifications(file_path=tmp_file_path)
            self.assertEqual(cm.exception.code, 1)
        finally:
            Path(tmp_file_path).unlink()

    def test_load_agent_specifications_missing_mandatory_field(self):
        sample_toml_content = """
[[agents]]
# name = "Test Agent 1" # Name is mandatory
description = "A test agent."
llm_model_name = "test-model-1"
data_classification = "public"
mcp_servers = ["server1", "server2"]
instructions = "Instructions for Test Agent 1."
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".toml") as tmp_file:
            tmp_file.write(sample_toml_content)
            tmp_file_path = tmp_file.name

        try:
            with self.assertRaises(SystemExit) as cm: # Pydantic validation error leads to SystemExit
                load_agent_specifications(file_path=tmp_file_path)
            self.assertEqual(cm.exception.code, 1)
        finally:
            Path(tmp_file_path).unlink()

if __name__ == "__main__":
    unittest.main()
