from datetime import timedelta

import pytest
from pydantic import BaseModel
from temporalio import activity
from temporalio.common import RetryPolicy

from temporal_utils.base_class import BaseActivityValidated, TemporalActivityValidators


class ActivityInput(BaseModel):
    operation: str


class ActivityOutput(BaseModel):
    result: str


act_options = {
    "start_to_close_timeout": timedelta(minutes=30),
    "retry_policy": RetryPolicy(
        initial_interval=timedelta(seconds=5),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=1),
        maximum_attempts=5,
        non_retryable_error_types=[],
    ),
}


def test_activity_has_its_own_call_options():
    class ActivityWithCallOptions(BaseActivityValidated):
        @activity.defn
        async def act_with_call_options(
            self, act_input: ActivityInput
        ) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_act_with_call_options = act_options


def test_activity_doesnt_have_its_own_call_options():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_has_a_default_opts.__name__,
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

        opts_activity_with_one_input = act_options


def test_activity_fails_with_more_than_one_input_arg():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_takes_a_single_arg.__name__,
    ):

        class ActivityWithTooManyInputs(BaseActivityValidated):
            @activity.defn
            async def act_with_too_many_inputs(
                self, act_input: ActivityInput, bad_arg: str = "bad"
            ) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_act_with_too_many_inputs = act_options


def test_activity_fails_with_no_input_arg():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_takes_a_single_arg.__name__,
    ):

        class ActivityWithNoInputArgs(BaseActivityValidated):
            @activity.defn
            async def activity_with_no_input_args(self) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_activity_with_no_input_args = act_options


def test_activity_fails_with_when_arg_isnt_pydantic():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_input_arg_is_pydantic_serializable.__name__,
    ):

        class ActivityWithArgDoesntJSONSerializeToDict(BaseActivityValidated):
            @activity.defn
            async def activity_with_invalid_arg(
                self, str_not_dict: str
            ) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_activity_with_invalid_arg = act_options


def test_activity_fails_with_when_output_isnt_pydantic():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_output_is_pydantic_serializable.__name__,
    ):

        class ActivityWithOneArg(BaseActivityValidated):
            @activity.defn
            async def activity_with_str_output(self, act_input: ActivityInput) -> str:
                return "success"

            opts_activity_with_str_output = act_options


def test_activity_fails_when_child_isnt_base_and_missing_activities():
    with pytest.raises(
        ValueError,
        match=TemporalActivityValidators.get_search_attribute(),
    ):

        class ClassWithoutActivitiesAndNotNamed_B_ase(BaseActivityValidated):
            pass


def test_activity_passes_when_base_class_missing_activities():
    class BaseClassShouldPassWithoutActivities(BaseActivityValidated):
        pass


def test_base_classes_can_be_grand_parents():
    class GrandParentBase(BaseActivityValidated):
        pass

    class ParentBase(GrandParentBase):
        pass

    class Child(ParentBase):
        @activity.defn
        async def activity(self, act_input: ActivityInput) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_activity = act_options


def test_activity_classes_can_be_grand_parents():
    class GrandParentBase(BaseActivityValidated):
        pass

    class ActivityParent(GrandParentBase):
        @activity.defn
        async def parent_activity(self, act_input: ActivityInput) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_parent_activity = act_options

    class ActivityChild(ActivityParent):
        @activity.defn
        async def child_activity(self, act_input: ActivityInput) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_child_activity = act_options

    class ActivityGrandChild(ActivityChild):
        @activity.defn
        async def grandchild_activity(self, act_input: ActivityInput) -> ActivityOutput:
            return ActivityOutput(result="success")

        opts_grandchild_activity = act_options


def test_activity_fails_when_input_is_base_model_but_also_dataclass():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_input_arg_is_pydantic_serializable.__name__,
    ):
        from dataclasses import dataclass

        @dataclass
        class BadInputIsDataclassAndBaseModel(BaseModel):
            operation: str

        class ActivityWithCallOptions(BaseActivityValidated):
            @activity.defn
            async def act_with_call_options(
                self, act_input: BadInputIsDataclassAndBaseModel
            ) -> ActivityOutput:
                return ActivityOutput(result="success")

            opts_act_with_call_options = act_options


def test_activity_fails_when_output_is_base_model_but_also_dataclass():
    with pytest.raises(
        TypeError,
        match=TemporalActivityValidators._validate_method_output_is_pydantic_serializable.__name__,
    ):
        from dataclasses import dataclass

        @dataclass
        class BadOutputIsDataclassAndBaseModel(BaseModel):
            result: str

        class ActivityWithCallOptions(BaseActivityValidated):
            @activity.defn
            async def act_with_call_options(
                self, act_input: ActivityInput
            ) -> BadOutputIsDataclassAndBaseModel:
                return BadOutputIsDataclassAndBaseModel(result="success")

            opts_act_with_call_options = act_options
