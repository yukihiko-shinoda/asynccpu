"""Model module of process task."""

from logging import getLogger

import psutil


class ProcessTask:
    """Represents a task running in a separate process.

    None of following specification is not required now. These specification will be removed if we got prospect that
    it's not required in the future too.

    This class is designed as:
    - Picklable to set SyncManager.list()
      E    object is not picklable
    - Hashable to use for key of weakset:
      E    TypeError: unhashable type

    Since psutil.Process is not picklable.

    see:
    Answer: python - Using an object's id() as a hash value - Stack Overflow
    https://stackoverflow.com/a/55086062/12721873
    Answer: python - What makes a user-defined class unhashable? - Stack Overflow
    https://stackoverflow.com/a/29434112/12721873
    Answer: python - How can I make class properties immutable? - Stack Overflow
    https://stackoverflow.com/a/43486647/12721873
    """

    def __init__(self, process_id: int) -> None:
        self._id = (process_id,)
        self.logger = getLogger(__name__)

    @property
    # Reason: It's no problem to consider that "id" is snake_case. pylint: disable=invalid-name
    def id(self) -> int:
        return self._id[0]

    def __hash__(self) -> int:
        return hash(self._id)

    def send_signal(self, signal_number: int) -> None:
        """Cancels task like future if its not cancelled."""
        try:
            psutil.Process(self.id).send_signal(signal_number)
        # Reason: Can't crate code to reach following line.
        except psutil.NoSuchProcess as error:  # pragma: no cover
            self.logger.debug("%s", error)
