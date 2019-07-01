from typing import Tuple, List

import yaml

from .parse_interfaces import Parser, ConsumerRecord, ProducerRecord


class YamlParser(Parser):
    def parse(self, yaml_content) -> Tuple[List[ConsumerRecord], List[ProducerRecord]]:
        interfaces = list(yaml.safe_load_all(yaml_content))
        return self._parse(interfaces)
