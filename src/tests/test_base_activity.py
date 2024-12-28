import pytest
from temporalio import activity
from pydantic import BaseModel

from temporal_utils.base_class import (
    BaseActivityValidated,
    TemporalActivityValidators,
)


class ActivityInput(BaseModel):
    operation: str


class ActivityOutput(BaseModel):
    result: str


def test_activity_has_its_own_call_options():
    class ActivityWithCallOptions(BaseActivityValidated):
        @activity.defn
        async def act_with_call_options(
            self, act_input: ActivityInput
        ) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_act_with_call_options = {}


def test_activity_doesnt_have_its_own_call_options():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_activity_has_a_default_ops.__name__,
    ):

        class ActivityWithoutOptions(BaseActivityValidated):
            @activity.defn
            async def activity_from_class_without_call_options_property(
                self,
                act_input: ActivityInput,
            ) -> ActivityOutput:
                return ActivityOutput(result="success")


def test_activity_succeeds_with_exactly_one_input_arg():
    class ActivityWithOneArg(BaseActivityValidated):
        @activity.defn
        async def activity_with_one_input(
            self, act_input: ActivityInput
        ) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_activity_with_one_input = {}


def test_activity_fails_with_more_than_one_input_arg():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_activity_takes_a_single_arg.__name__,
    ):

        class ActivityWithTooManyInputs(BaseActivityValidated):
            @activity.defn
            async def act_with_too_many_inputs(
                self, act_input: ActivityInput, bad_arg: str = "bad"
            ) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_act_with_too_many_inputs = {}


def test_activity_fails_with_no_input_arg():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_activity_takes_a_single_arg.__name__,
    ):

        class ActivityWithNoInputArgs(BaseActivityValidated):
            @activity.defn
            async def activity_with_no_input_args(self) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_activity_with_no_input_args = {}


def test_activity_fails_with_when_arg_isnt_pydantic():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_activity_input_arg_is_pydantic_serializable.__name__,
    ):

        class ActivityWithArgDoesntJSONSerializeToDict(BaseActivityValidated):
            @activity.defn
            async def activity_with_invalid_arg(
                self, str_not_dict: str
            ) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_activity_with_invalid_arg = {}


def test_activity_fails_with_when_output_isnt_pydantic():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_activity_output_is_pydantic_serializable.__name__,
    ):

        class ActivityWithOneArg(BaseActivityValidated):
            @activity.defn
            async def activity_with_str_output(self, act_input: ActivityInput) -> str:
                return "success"

            opts_activity_with_str_output = {}
