"""Opt into a physical polynomial x base without relaxing the public trig parser."""

from .exam_exponential import X
from .exam_trigonometric_log_variable import Parser
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_parser import Node


class ScalarAngle(ExamAngleParser):
    implicit_prefixes = (*ExamAngleParser.implicit_prefixes, r"\alpha")

    def _nested(self, text):
        return ScalarAngle(text, self.atoms, self.denominators, self.depth + 1).parse()

    def _primary(self):
        if self.text.startswith(r"\alpha", self.index):
            self.index += 6
            return Node(X, "x")
        return super()._primary()


class ScalarLogParser(Parser):
    base_parser = ScalarAngle
    implicit_prefixes = (*Parser.implicit_prefixes, r"\alpha")

    def _primary(self):
        if self.text.startswith(r"\alpha", self.index):
            self.index += 6
            return Node(X, "x")
        return super()._primary()
