from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class HiddenInput:
    input_value: int = 1

def hidden_callback():
    return HiddenInput()

def enclosing_local_root(callback):
    local = callback
    def child():
        return local()
    return child()

class CallbackView(Protocol):
    def compute(self): ...

class HiddenImplementation:
    def compute(self):
        return HiddenInput()

def protocol_root(view: CallbackView):
    return view.compute()

DISPATCH = {'chosen': hidden_callback}
def dict_root(key):
    return DISPATCH[key]()

MODULE = None
def getattr_root(key):
    return getattr(MODULE, key)()

@dataclass(frozen=True)
class Config:
    multiplier: int = 2

@dataclass(frozen=True)
class PublicRecord:
    value: int = 0
    def __post_init__(self):
        object.__setattr__(self, 'value', Config().multiplier)
    @property
    def result(self):
        return hidden_callback()

def post_init_root():
    return PublicRecord()

def property_root(record: PublicRecord):
    return record.result
