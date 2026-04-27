from __future__ import annotations

from collections import Counter
import functools
import weakref
from typing import Any, Callable

import torch
from torch._subclasses import FakeTensorMode
from torch.utils._python_dispatch import TorchDispatchMode
from torch.utils._pytree import tree_map_only
from torch.utils.weak import WeakIdKeyDictionary


MB = 2 ** 20
GB = 2 ** 30


def tensor_storage_id(tensor: torch.Tensor) -> int:
    return tensor._typed_storage()._cdata


class FakeTensorMemoryProfilerMode(TorchDispatchMode):
    def __init__(self) -> None:
        self.storage_count: dict[int, int] = Counter()
        self.live_tensors = WeakIdKeyDictionary()
        self.memory_use = 0
        self.max_memory = 0

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        kwargs = kwargs if kwargs is not None else {}
        result = func(*args, **kwargs)
        tree_map_only(torch._subclasses.FakeTensor, self.track_tensor_memory_use, result)
        return result

    def track_tensor_memory_use(self, tensor: torch.Tensor) -> None:
        if tensor in self.live_tensors:
            return

        self.live_tensors[tensor] = True
        nbytes = tensor.untyped_storage().nbytes()
        storage_id = tensor_storage_id(tensor)

        if storage_id not in self.storage_count:
            self.change_memory(nbytes)

        self.storage_count[storage_id] += 1
        weakref.finalize(
            tensor,
            functools.partial(self.tensor_cleanup, storage_id, nbytes),
        )

    def tensor_cleanup(self, storage_id: int, nbytes: int) -> None:
        self.storage_count[storage_id] -= 1
        if self.storage_count[storage_id] == 0:
            del self.storage_count[storage_id]
            self.change_memory(-nbytes)

    def change_memory(self, delta: int) -> None:
        self.memory_use += delta
        self.max_memory = max(self.memory_use, self.max_memory)


def estimate_faketensor_memory(
    model,
    *,
    input_builder: Callable[[], Any],
    forward_call: Callable[[Any], Any],
    run_backward: bool = True,
) -> int:
    with FakeTensorMode(allow_non_fake_inputs=True):
        with FakeTensorMemoryProfilerMode() as profiler:
            fake_inputs = input_builder()
            output = forward_call(fake_inputs)

            if run_backward:
                if isinstance(output, torch.Tensor):
                    output.sum().backward()
                else:
                    raise TypeError(
                        "run_backward=True requires forward_call to return a Tensor"
                    )

            return profiler.max_memory


def format_memory_gib(memory_bytes: int) -> float:
    return memory_bytes / GB