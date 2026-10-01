"""
Created on 2026-10-01

@author: wf
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

import yaml

from ceursemantify import model
from ceursemantify.convert import Convert


@dataclass
class MappingIssue:
    """
    a source value that could not be mapped
    """

    target_class: str
    source_key: str
    message: str

    def __str__(self) -> str:
        text = f"{self.target_class}: {self.source_key}: {self.message}"
        return text


@dataclass
class MappingResult:
    """
    the result of mapping one source record
    """

    target: Any = None
    issues: List[MappingIssue] = field(default_factory=list)


class Mapper:
    """
    map source records to the research model as declared in a mapping table
    """

    def __init__(self, mapping: Dict[str, Any]):
        """
        constructor

        Args:
            mapping: the mapping table: per target class the fields and the ignored source keys
        """
        self.mapping = mapping

    @classmethod
    def default_mapping_path(cls) -> str:
        """
        get the path of the mapping table for the JSON-LD of ceur-spt

        Returns:
            str: the path of resources/ceurspt_mapping.yaml
        """
        path = os.path.join(os.path.dirname(__file__), "resources", "ceurspt_mapping.yaml")
        return path

    @classmethod
    def of_yaml(cls, path: Optional[str] = None) -> "Mapper":
        """
        create a mapper from the given mapping table

        Args:
            path: the path of the yaml file, the ceur-spt mapping if None

        Returns:
            Mapper: the mapper
        """
        if path is None:
            path = cls.default_mapping_path()
        with open(path, "r", encoding="utf-8") as mapping_file:
            mapping = yaml.safe_load(mapping_file)
        mapper = cls(mapping)
        return mapper

    def target_class(self, class_name: str) -> Type:
        """
        get the class of the research model with the given name

        Args:
            class_name: the name of the class e.g. Proceedings

        Returns:
            Type: the class
        """
        target_class = getattr(model, class_name)
        return target_class

    def convert(self, value: Any, rule: Dict[str, Any], result: MappingResult) -> Any:
        """
        convert a source value according to the given rule

        Args:
            value: the source value
            rule: the rule of the mapping table for the target field
            result: the mapping result to add issues to

        Returns:
            Any: the converted value, None if the value could not be converted
        """
        converted = value
        nested_class = rule.get("class")
        conversion = rule.get("as")
        if nested_class:
            converted = self.map_nested(value, nested_class, rule.get("into"), result)
        elif conversion:
            converted = getattr(Convert, conversion)(value)
        return converted

    def map_nested(self, value: Any, class_name: str, into: Optional[str], result: MappingResult) -> Any:
        """
        map a nested source value to an object or a list of objects

        Args:
            value: a source record, a list of source records or a plain value
            class_name: the name of the target class
            into: the field of the target class that takes a plain value
            result: the mapping result to add issues to

        Returns:
            Any: the object or list of objects
        """
        if isinstance(value, list):
            nested = [self.map_nested(item, class_name, into, result) for item in value]
        elif isinstance(value, dict):
            nested_result = self.map_record(value, class_name)
            result.issues.extend(nested_result.issues)
            nested = nested_result.target
        elif into:
            nested = self.target_class(class_name)(**{into: Convert.text(value)})
        else:
            raise ValueError(f"plain value {value} for {class_name} without into field")
        return nested

    def map_record(self, record: Dict[str, Any], class_name: str) -> MappingResult:
        """
        map the given source record to an object of the given class

        Source keys that are neither mapped nor ignored and values that can
        not be converted are reported as issues.

        Args:
            record: the source record
            class_name: the name of the target class e.g. Proceedings

        Returns:
            MappingResult: the object and the issues
        """
        result = MappingResult()
        class_mapping = self.mapping[class_name]
        rules = class_mapping.get("fields") or {}
        ignored = class_mapping.get("ignore") or {}
        values = {}
        mapped_keys = set()
        for target_field, rule in rules.items():
            source_key = rule["from"]
            mapped_keys.add(source_key)
            value = record.get(source_key)
            if value is None or value == "":
                continue
            try:
                values[target_field] = self.convert(value, rule, result)
            except ValueError as error:
                result.issues.append(MappingIssue(class_name, source_key, str(error)))
        for source_key in record:
            if source_key not in mapped_keys and source_key not in ignored:
                result.issues.append(MappingIssue(class_name, source_key, "not in the mapping table"))
        result.target = self.target_class(class_name)(**values)
        return result
