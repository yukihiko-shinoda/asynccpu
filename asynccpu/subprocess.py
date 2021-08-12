"""Subprocess."""


class ProcessForWeakSet:
    """
    Requirement of this class:
    - Picklable to set SyncManager.list()
      object is not picklable
    - Hashable to use key of weakset:
      TypeError: unhashable type
      see:
        Answer: python - Using an object's id() as a hash value - Stack Overflow
        https://stackoverflow.com/a/55086062/12721873
        Answer: python - What makes a user-defined class unhashable? - Stack Overflow
        https://stackoverflow.com/a/29434112/12721873
        Answer: python - How can I make class properties immutable? - Stack Overflow
        https://stackoverflow.com/a/43486647/12721873
    Since psutil.Process is not picklable.
    """

    def __init__(self, process_id: int) -> None:
        self._id = (process_id,)

    @property
    # Reason: It's no problem to consider that "id" is snake_case. pylint: disable=invalid-name
    def id(self) -> int:
        return self._id[0]

    def __hash__(self) -> int:
        return hash(self._id)
