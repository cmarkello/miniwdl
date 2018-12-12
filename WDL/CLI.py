"""
miniwdl command-line interface
"""
import sys
import os
from argparse import ArgumentParser
import WDL
import WDL.Lint


def main(args=None):
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    subparsers.required = True
    subparsers.dest = "command"

    check_parser = subparsers.add_parser(
        "check", help="Load and typecheck a WDL document; show an outline with lint warnings"
    )
    check_parser.add_argument("uri", metavar="URI", type=str, help="WDL document filename/URI")
    check_parser.add_argument(
        "-p",
        "--path",
        metavar="DIR",
        type=str,
        action="append",
        help="local directory to search for imports",
    )
    check_parser.add_argument(
        "--no-quant-check",
        dest="check_quant",
        action="store_false",
        help="relax static typechecking of optional (?) and nonempty (+) type quantifiers (discouraged; for backwards compatibility with older WDL)",
    )

    args = parser.parse_args(args if args is not None else sys.argv[1:])

    if args.command == "check":
        check(args)
    else:
        assert False


def check(args):
    # Load the document (read, parse, and typecheck)
    if args.path is None:
        args.path = []
    doc = WDL.load(args.uri, args.path, check_quant=args.check_quant)

    WDL.Lint.lint(doc)

    # Print an outline
    print(os.path.basename(args.uri))
    outline(doc, 0)


# recursively pretty-print a brief outline of the workflow


def outline(obj, level, file=sys.stdout):
    s = "".join(" " for i in range(level * 4))

    first_descent = []

    def descend(dobj=None, first_descent=first_descent):
        # show lint for the node just prior to first descent beneath it
        if not first_descent and hasattr(obj, "lint"):
            for (node, klass, msg) in sorted(obj.lint, key=lambda t: t[0].pos):
                print(
                    "{}    (Ln {}, Col {}) {}, {}".format(
                        s, node.pos.line, node.pos.column, klass, msg
                    ),
                    file=file,
                )
        first_descent.append(False)
        if dobj:
            outline(dobj, level + (1 if not isinstance(dobj, WDL.Decl) else 0), file=file)

    # document
    if isinstance(obj, WDL.Document):
        # workflow
        if obj.workflow:
            descend(obj.workflow)
        # tasks
        for task in sorted(obj.tasks, key=lambda task: (not task.called, task.name)):
            descend(task)
        # imports
        for uri, namespace, subdoc in sorted(obj.imports, key=lambda t: t[1]):
            print("    {}{} : {}".format(s, namespace, os.path.basename(uri)), file=file)
            descend(subdoc)
    # workflow
    elif isinstance(obj, WDL.Workflow):
        print(
            "{}workflow {}{}".format(s, obj.name, " (not called)" if not obj.called else ""),
            file=file,
        )
        for elt in obj.elements:
            descend(elt)
    # task
    elif isinstance(obj, WDL.Task):
        print(
            "{}task {}{}".format(s, obj.name, " (not called)" if not obj.called else ""), file=file
        )
        for decl in (obj.inputs or []) + obj.postinputs + obj.outputs:
            descend(decl)
    # call
    elif isinstance(obj, WDL.Call):
        if obj.name != obj.callee_id.name:
            print(
                "{}call {} as {}".format(
                    s, ".".join(obj.callee_id.namespace + [obj.callee_id.name]), obj.name
                ),
                file=file,
            )
        else:
            print(
                "{}call {}".format(s, ".".join(obj.callee_id.namespace + [obj.callee_id.name])),
                file=file,
            )
    # scatter
    elif isinstance(obj, WDL.Scatter):
        print("{}scatter {}".format(s, obj.variable), file=file)
        for elt in obj.elements:
            descend(elt)
    # if
    elif isinstance(obj, WDL.Conditional):
        print("{}if".format(s), file=file)
        for elt in obj.elements:
            descend(elt)
    # decl
    elif isinstance(obj, WDL.Decl):
        pass

    descend()
