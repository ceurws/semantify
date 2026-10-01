"""
Created on 2026-10-01

@author: wf
"""

import dataclasses
import json
import os
from typing import Any, Dict, Optional

import yaml

from ceursemantify.model import Paper, Proceedings


class JsonLd:
    """
    JSON-LD of the research model according to the context table
    resources/context.yaml
    """

    def __init__(self, table: Dict[str, Any]):
        """
        constructor

        Args:
            table: the context table: namespaces, provisional terms and classes
        """
        self.table = table
        self.classes = table["classes"]

    @classmethod
    def default_table_path(cls) -> str:
        """
        get the path of the context table

        Returns:
            str: the path of resources/context.yaml
        """
        path = os.path.join(os.path.dirname(__file__), "resources", "context.yaml")
        return path

    @classmethod
    def of_yaml(cls, path: Optional[str] = None) -> "JsonLd":
        """
        create the JSON-LD support from the given context table

        Args:
            path: the path of the yaml file, the default table if None

        Returns:
            JsonLd: the JSON-LD support
        """
        if path is None:
            path = cls.default_table_path()
        with open(path, "r", encoding="utf-8") as table_file:
            table = yaml.safe_load(table_file)
        jsonld = cls(table)
        return jsonld

    def term_definition(self, term: Dict[str, Any]) -> Dict[str, Any]:
        """
        get the JSON-LD term definition for the given row of the context table

        Args:
            term: the row: id or reverse, optionally type and container

        Returns:
            Dict[str, Any]: the term definition
        """
        definition = {}
        if "reverse" in term:
            definition["@reverse"] = term["reverse"]
        else:
            definition["@id"] = term["id"]
        if "type" in term:
            definition["@type"] = term["type"]
        if "container" in term:
            definition["@container"] = term["container"]
        return definition

    def context(self) -> Dict[str, Any]:
        """
        get the JSON-LD context: the namespaces and per class a type scoped
        context with the terms of its fields

        Returns:
            Dict[str, Any]: the value of @context
        """
        context: Dict[str, Any] = {"@version": 1.1}
        context.update(self.table["namespaces"])
        for class_name, class_row in self.classes.items():
            scoped = {}
            for field_name, term in class_row["terms"].items():
                scoped[field_name] = self.term_definition(term)
            context[class_name] = {"@id": class_row["type"], "@context": scoped}
        return context

    def node(self, instance: Any) -> Dict[str, Any]:
        """
        get the JSON-LD node of the given object of the research model

        Fields without value are left out.

        Args:
            instance: the object e.g. a Proceedings

        Returns:
            Dict[str, Any]: the node with @type and, if the class has an id field, @id
        """
        class_name = type(instance).__name__
        class_row = self.classes[class_name]
        node: Dict[str, Any] = {"@type": class_name}
        id_field = class_row.get("id_field")
        if id_field and getattr(instance, id_field):
            node["@id"] = getattr(instance, id_field)
        for field in dataclasses.fields(instance):
            value = getattr(instance, field.name)
            if value is None or value == []:
                continue
            if dataclasses.is_dataclass(value):
                value = self.node(value)
            elif isinstance(value, list):
                value = [self.node(item) for item in value]
            node[field.name] = value
        return node

    def document(self, instance: Any) -> Dict[str, Any]:
        """
        get the JSON-LD document of the given object of the research model

        Args:
            instance: the object e.g. a Proceedings or a Paper

        Returns:
            Dict[str, Any]: the document with @context
        """
        document = {"@context": self.context()}
        document.update(self.node(instance))
        return document

    def as_text(self, instance: Any) -> str:
        """
        get the pretty printed JSON-LD document of the given object

        Args:
            instance: the object e.g. a Proceedings or a Paper

        Returns:
            str: the JSON-LD with an indent of two
        """
        text = json.dumps(self.document(instance), indent=2, ensure_ascii=False)
        return text

    def plain(self, value: Any) -> Any:
        """
        remove the JSON-LD keywords from the given value

        Args:
            value: a node, a list of nodes or a plain value

        Returns:
            Any: the value without the keys that start with @
        """
        plain = value
        if isinstance(value, dict):
            plain = {key: self.plain(item) for key, item in value.items() if not key.startswith("@")}
        elif isinstance(value, list):
            plain = [self.plain(item) for item in value]
        return plain

    def proceedings(self, document: Dict[str, Any]) -> Proceedings:
        """
        get the proceedings of the given JSON-LD document

        Args:
            document: a document as created by the document method

        Returns:
            Proceedings: the proceedings
        """
        proceedings = Proceedings.from_dict(self.plain(document))
        return proceedings

    def paper(self, document: Dict[str, Any]) -> Paper:
        """
        get the paper of the given JSON-LD document

        Args:
            document: a document as created by the document method for a paper

        Returns:
            Paper: the paper
        """
        paper = Paper.from_dict(self.plain(document))
        return paper
