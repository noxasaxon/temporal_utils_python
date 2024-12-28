import pytest
from temporalio import workflow
from pydantic import BaseModel

from temporal_utils.base_class import (
    # BaseActivityValidated,
    TemporalWorkflowValidators,
    BaseWorkflowValidated,
)


class WorkflowInput(BaseModel):
    operation: str


class WorkflowOutput(BaseModel):
    result: str


### BEGIN TESTS ####

# Cant use test functions because temporalio's decorator throws when it is used on a class def in a local function
with pytest.raises(
    TypeError,
    match=TemporalWorkflowValidators._validate_method_has_a_default_opts.__name__,
):

    @workflow.defn
    class BadWorkflowMissingRunOptions(BaseWorkflowValidated):
        @workflow.run
        async def run(self, wf_input: WorkflowInput) -> WorkflowOutput:
            return WorkflowOutput(result="success")


def test_wf_is_missing_run_opts_above():
    pass


with pytest.raises(
    TypeError,
    match=TemporalWorkflowValidators._validate_method_takes_a_single_arg.__name__,
):

    @workflow.defn
    class BadWorkflowMultipleInputs(BaseWorkflowValidated):
        @workflow.run
        async def run(
            self, wf_input: WorkflowInput, second_arg: WorkflowInput
        ) -> WorkflowOutput:
            return WorkflowOutput(result="success")

        opts_run = {}


def test_wf_has_multiple_inputs_above():
    pass


with pytest.raises(
    TypeError,
    match=TemporalWorkflowValidators._validate_method_takes_a_single_arg.__name__,
):

    @workflow.defn
    class BadWorkflowNoInput(BaseWorkflowValidated):
        @workflow.run
        async def run(self) -> WorkflowOutput:
            return WorkflowOutput(result="success")

        opts_run = {}


def test_wf_has_no_input_above():
    pass


with pytest.raises(
    TypeError,
    match=TemporalWorkflowValidators._validate_method_input_arg_is_pydantic_serializable.__name__,
):

    @workflow.defn
    class BadWorkflowNotPydanticInput(BaseWorkflowValidated):
        @workflow.run
        async def run(self, wf_input: str) -> WorkflowOutput:
            return WorkflowOutput(result="success")

        opts_run = {}


def test_wf_has_non_pydantic_input_above():
    pass


with pytest.raises(
    TypeError,
    match=TemporalWorkflowValidators._validate_method_output_is_pydantic_serializable.__name__,
):

    @workflow.defn
    class BadWorkflowNotPydanticOutput(BaseWorkflowValidated):
        @workflow.run
        async def run(self, wf_input: WorkflowInput) -> str:
            return "success"

        opts_run = {}


def test_wf_has_non_pydantic_output_above():
    pass
