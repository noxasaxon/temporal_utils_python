from datetime import timedelta
from typing import Any
from pydantic import BaseModel
import pytest
from temporalio import activity
from temporalio.common import RetryPolicy

from temporal_utils.base_class import BaseActivityValidated
from temporal_utils.validation import _BaseValidator


class ActivityInput(BaseModel):
    operation: str


class ActivityOutput(BaseModel):
    result: str


class BadValidatorMissingSearchAttribute(_BaseValidator):
    # we didnt set the search attribute method
    pass


class BadBaseActivityUsingBadValidator:
    def __init_subclass__(cls: type, **kwargs: dict[str, Any]) -> None:
        """Automatically runs the `TemporalActivityValidators` validations on all children, even without instantiation."""
        BadValidatorMissingSearchAttribute().run_validators(cls)

        # continue with normal subclass initialization
        super().__init_subclass__(**kwargs)  # type: ignore[misc]


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


class SuccessfulActivity(BaseActivityValidated):
    @activity.defn
    async def act_with_call_options(self, act_input: ActivityInput) -> ActivityOutput:
        return ActivityOutput(result="success")

    opts_act_with_call_options = act_options


class GoodActivityWithNoBase:
    """Used by creating a new class that inherits from this class, and then a base activity class with a validator attached via init_subclass."""

    @activity.defn
    async def act_with_call_options(self, act_input: ActivityInput) -> ActivityOutput:
        return ActivityOutput(result="success")

    opts_act_with_call_options = act_options


def test_successful_activity_is_still_correct():
    class GoodActivityWithGoodValidator(GoodActivityWithNoBase, BaseActivityValidated):
        pass


def test_validator_subclass_fails_when_search_attribute_isnt_set():
    with pytest.raises(NotImplementedError):

        class GoodActivityWithBadValidator(
            GoodActivityWithNoBase, BadBaseActivityUsingBadValidator
        ):
            opts_act_with_call_options = act_options
