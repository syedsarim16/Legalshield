"""Small Firestore repository with the query operations used by the API."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterator

from google.cloud.firestore_v1 import transactional

from .firebase import firestore_client
from .utils import new_id


@dataclass(frozen=True)
class Condition:
    field: str
    operator: str
    value: Any
    transform: str | None = None

    def matches(self, values: dict) -> bool:
        actual = values.get(self.field)
        expected = self.value
        if self.transform == "upper" and isinstance(actual, str):
            actual = actual.upper()
        try:
            if self.operator == "==":
                return actual == expected
            if self.operator == "!=":
                return actual != expected
            if self.operator == ">=":
                return actual >= expected
            if self.operator == ">":
                return actual > expected
            if self.operator == "<=":
                return actual <= expected
            if self.operator == "<":
                return actual < expected
            raise ValueError(f"Unsupported operator: {self.operator}")
        except (TypeError, KeyError):
            return False

    def __or__(self, other: Condition | CombinedCondition) -> CombinedCondition:
        return CombinedCondition("or", (self, other))

    def __and__(self, other: Condition | CombinedCondition) -> CombinedCondition:
        return CombinedCondition("and", (self, other))


@dataclass(frozen=True)
class CombinedCondition:
    operator: str
    conditions: tuple[Condition | CombinedCondition, ...]

    def matches(self, values: dict) -> bool:
        matches = (condition.matches(values) for condition in self.conditions)
        return any(matches) if self.operator == "or" else all(matches)

    def __or__(self, other: Condition | CombinedCondition) -> CombinedCondition:
        return CombinedCondition("or", (self, other))

    def __and__(self, other: Condition | CombinedCondition) -> CombinedCondition:
        return CombinedCondition("and", (self, other))


class Field:
    def __init__(self, name: str):
        self.name = name

    def __get__(self, instance, owner):
        return self if instance is None else instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def __eq__(self, other):
        return Condition(self.name, "==", other)

    def __ne__(self, other):
        return Condition(self.name, "!=", other)

    def __ge__(self, other):
        return Condition(self.name, ">=", other)

    def __gt__(self, other):
        return Condition(self.name, ">", other)

    def __le__(self, other):
        return Condition(self.name, "<=", other)

    def __lt__(self, other):
        return Condition(self.name, "<", other)

    def desc(self):
        return (self.name, True)

    def asc(self):
        return (self.name, False)


class Count:
    pass


class Functions:
    @staticmethod
    def count():
        return Count()

    @staticmethod
    def upper(field: Field) -> TransformedField:
        return TransformedField(field.name, "upper")


class TransformedField(Field):
    def __init__(self, name: str, transform: str):
        super().__init__(name)
        self.transform = transform

    def __eq__(self, other):
        return Condition(self.name, "==", other, self.transform)


func = Functions()


class Select:
    def __init__(self, model):
        self.model = model
        self.conditions: list[Condition | CombinedCondition] = []
        self.ordering: list[tuple[str, bool]] = []
        self.count_only = False

    def where(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def order_by(self, *fields):
        self.ordering.extend(fields)
        return self

    def select_from(self, model):
        self.model = model
        self.count_only = True
        return self


class Update:
    def __init__(self, model):
        self.model = model
        self.conditions = []
        self.values_to_set = {}

    def where(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def values(self, **values):
        self.values_to_set = values
        return self


class Delete:
    def __init__(self, model):
        self.model = model
        self.conditions = []

    def where(self, *conditions):
        self.conditions.extend(conditions)
        return self


def select(model) -> Select:
    return Select(model)


def update(model) -> Update:
    return Update(model)


def delete(model) -> Delete:
    return Delete(model)


class FirestoreSession:
    def __init__(self, client):
        self.client = client
        self._pending: list[Any] = []
        self._deleted: list[Any] = []
        self._tracked: dict[tuple[type, str], tuple[Any, dict]] = {}

    @staticmethod
    def _state(item) -> dict:
        return {name: copy.deepcopy(getattr(item, name)) for name in item.__fields__}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _key(model, item) -> str:
        key = getattr(model, "__key__", "id")
        value = getattr(item, key, None)
        if value is None:
            value = new_id()
            setattr(item, key, value)
        return str(value)

    def _collection(self, model):
        return self.client.collection(model.__collection__)

    def get(self, model, key):
        snapshot = self._collection(model).document(str(key)).get()
        if not snapshot.exists:
            return None
        values = snapshot.to_dict() or {}
        values[getattr(model, "__key__", "id")] = str(key)
        item = model.from_dict(values)
        self._tracked[(model, str(key))] = (item, self._state(item))
        return item

    def _rows(self, query: Select) -> list:
        collection = self._collection(query.model)
        conditions = query.conditions
        snapshots = None
        if conditions and isinstance(conditions[0], Condition) and conditions[0].transform is None:
            condition = conditions[0]
            snapshots = collection.where(condition.field, condition.operator, condition.value).stream()
            conditions = conditions[1:]
        elif len(conditions) == 1 and isinstance(conditions[0], CombinedCondition) and conditions[0].operator == "or":
            snapshots_by_id = {}
            for condition in conditions[0].conditions:
                if isinstance(condition, Condition) and condition.transform is None:
                    filtered = collection.where(condition.field, condition.operator, condition.value)
                    for snapshot in filtered.stream():
                        snapshots_by_id[snapshot.id] = snapshot
                else:
                    for snapshot in collection.stream():
                        values = snapshot.to_dict() or {}
                        if condition.matches(values):
                            snapshots_by_id[snapshot.id] = snapshot
            snapshots = snapshots_by_id.values()
            conditions = []
        if snapshots is None:
            snapshots = collection.stream()
        rows = []
        for snapshot in snapshots:
            values = snapshot.to_dict() or {}
            values[getattr(query.model, "__key__", "id")] = str(snapshot.id)
            if not all(condition.matches(values) for condition in conditions):
                continue
            item = query.model.from_dict(values)
            self._tracked[(query.model, str(snapshot.id))] = (item, self._state(item))
            rows.append(item)
        for field, descending in reversed(query.ordering):
            rows.sort(key=lambda item: getattr(item, field) or 0, reverse=descending)
        return rows

    def scalar(self, query):
        if isinstance(query, Select):
            rows = self._rows(query)
            return len(rows) if query.count_only else (rows[0] if rows else None)
        raise TypeError("Unsupported Firestore scalar query.")

    def scalars(self, query):
        return iter(self._rows(query))

    def query(self, model):
        return QueryView(self, model)

    def add(self, item):
        self._pending.append(item)

    def flush(self):
        for item in self._pending:
            self._key(type(item), item)

    def delete(self, item):
        self._deleted.append(item)

    def execute(self, query):
        if isinstance(query, Update):
            rows = self._rows(Select(query.model).where(*query.conditions))
            updated = 0
            for row in rows:
                model = type(row)
                key = self._key(model, row)
                reference = self._collection(model).document(key)

                @transactional
                def update_if_matches(transaction):
                    snapshot = reference.get(transaction=transaction)
                    if not snapshot.exists:
                        return False
                    values = snapshot.to_dict() or {}
                    values[getattr(model, "__key__", "id")] = key
                    if not all(condition.matches(values) for condition in query.conditions):
                        return False
                    transaction.update(reference, query.values_to_set)
                    return True

                if update_if_matches(self.client.transaction()):
                    updated += 1
            return WriteResult(updated)
        if isinstance(query, Delete):
            rows = self._rows(Select(query.model).where(*query.conditions))
            self._deleted.extend(rows)
            return WriteResult(len(rows))
        raise TypeError("Unsupported Firestore statement.")

    def commit(self):
        writes: dict[tuple[type, str], Any] = {}
        for item in self._pending:
            model = type(item)
            writes[(model, self._key(model, item))] = item
        self._pending.clear()
        deleted = self._deleted
        self._deleted = []
        deleted_keys = {(type(item), self._key(type(item), item)) for item in deleted}
        for item in deleted:
            model = type(item)
            writes.pop((model, self._key(model, item)), None)
        for (_, key), (item, original) in list(self._tracked.items()):
            if (type(item), key) not in deleted_keys and self._state(item) != original:
                writes[(type(item), key)] = item
        operations = [("set", model, key, item) for (model, key), item in writes.items()]
        operations.extend(("delete", type(item), self._key(type(item), item), item) for item in deleted)
        if operations:
            for start in range(0, len(operations), 450):
                batch = self.client.batch()
                for operation, model, key, item in operations[start:start + 450]:
                    reference = self._collection(model).document(key)
                    if operation == "set":
                        batch.set(reference, item.to_dict())
                    else:
                        batch.delete(reference)
                batch.commit()
        for model_key, item in writes.items():
            self._tracked[model_key] = (item, self._state(item))

    def _save(self, item):
        model = type(item)
        key = self._key(model, item)
        self._collection(model).document(key).set(item.to_dict())

    def rollback(self):
        self._pending.clear()
        self._deleted.clear()
        self._tracked.clear()

    def close(self):
        self.rollback()


class WriteResult:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class QueryView:
    def __init__(self, session: FirestoreSession, model):
        self.session = session
        self.model = model
        self.conditions = []

    def filter_by(self, **kwargs):
        self.conditions.extend(Condition(key, "==", value) for key, value in kwargs.items())
        return self

    def one(self):
        rows = self.all()
        if len(rows) != 1:
            raise LookupError(f"Expected one Firestore record, found {len(rows)}.")
        return rows[0]

    def all(self):
        return self.session._rows(Select(self.model).where(*self.conditions))

    def count(self):
        return len(self.all())


def get_db() -> Iterator[FirestoreSession]:
    session = FirestoreSession(firestore_client())
    try:
        yield session
    finally:
        session.close()
