import unittest
import logging
import tempfile
from .context import WDL

class TestStdLib(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')
        self._dir = tempfile.mkdtemp(prefix="miniwdl_test_stdlib_")

    def _test_task(self, wdl:str, inputs = None, expected_exception: Exception = None):
        doc = WDL.parse_document(wdl)
        assert len(doc.tasks) == 1
        doc.typecheck()
        if isinstance(inputs, dict):
            inputs = WDL.values_from_json(inputs, doc.tasks[0].available_inputs, doc.tasks[0].required_inputs)
        if expected_exception:
            try:
                WDL.runtime.run_local_task(doc.tasks[0], (inputs or []), parent_dir=self._dir)
            except WDL.runtime.task.TaskFailure as exn:
                self.assertIsInstance(exn.__context__, expected_exception)
                return exn.__context__
            self.assertFalse(str(expected_exception) + " not raised")
        rundir, outputs = WDL.runtime.run_local_task(doc.tasks[0], (inputs or []), parent_dir=self._dir)
        return WDL.values_to_json(outputs)

    def test_size_polytype(self):
        tmpl = """
        version 1.0
        task test_size {{
            input {{
                File file1
                File file2
            }}
            {}
            command <<<
                echo "nop"
            >>>
        }}
        """

        for case in [
            "Float sz = size(file1)",
            "Float sz = size(file1, 'GB')",
            "Float sz = size([file1,file2], 'KB')",
            "Float sz = size([file1,file2], 'KB')",
        ]:
            doc = WDL.parse_document(tmpl.format(case))
            doc.typecheck()

        for case in [
            ("Float sz = size()", WDL.Error.WrongArity),
            ("Float sz = size(file1,file2,'MB')", WDL.Error.WrongArity),
            ("Float sz = size(42)", WDL.Error.StaticTypeMismatch),
            ("Float sz = size([42])", WDL.Error.StaticTypeMismatch),
            ("Float sz = size(file1,file2)", WDL.Error.StaticTypeMismatch),
            ("Float sz = size(file1,[file2])", WDL.Error.StaticTypeMismatch),
        ]:
            doc = WDL.parse_document(tmpl.format(case[0]))
            with self.assertRaises(case[1]):
                doc.typecheck()

    def test_length(self):
        outputs = self._test_task(R"""
        version 1.0
        task test_length {
            command {}
            output {
                Int l0 = length([])
                Int l1 = length([42])
                Int l2 = length([42,43])
            }
        }
        """)
        self.assertEqual(outputs, {"l0": 0, "l1": 1, "l2" : 2})
