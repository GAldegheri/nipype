"""Parallel workflow execution via PBS/Torque
"""

import os
from time import sleep

from ... import logging
from ...interfaces.base import CommandLine
from .base import SGELikeBatchManagerBase, logger

iflogger = logging.getLogger("nipype.interface")


class PBSPlugin(SGELikeBatchManagerBase):
    """Execute using PBS/Torque

    The plugin_args input to run can be used to control the SGE execution.
    Currently supported options are:

    - template : template to use for batch job submission
    - qsub_args : arguments to be prepended to the job execution script in the
                  qsub call
    - max_jobname_len: maximum length of the job name.  Default 15.

    """

    # Additional class variables
    _max_jobname_len = 15

    def __init__(self, **kwargs):
        template = """
#PBS -V
        """
        self._retry_timeout = 2
        self._max_tries = 2
        self._max_jobname_length = 15
        if "plugin_args" in kwargs and kwargs["plugin_args"]:
            if "retry_timeout" in kwargs["plugin_args"]:
                self._retry_timeout = kwargs["plugin_args"]["retry_timeout"]
            if "max_tries" in kwargs["plugin_args"]:
                self._max_tries = kwargs["plugin_args"]["max_tries"]
            if "max_jobname_len" in kwargs["plugin_args"]:
                self._max_jobname_len = kwargs["plugin_args"]["max_jobname_len"]
        super().__init__(template, **kwargs)

    def _is_pending(self, taskid):
        result = CommandLine(
            f"qstat -f {taskid}",
            environ=dict(os.environ),
            terminal_output="file_split",
            resource_monitor=False,
            ignore_exception=True,
        ).run()

        stdout = result.runtime.stdout
        stderr = result.runtime.stderr
        errmsg = "Unknown Job Id"
        success = "Job has finished"
        if (success in stderr) or ("job_state = C" in stdout):
            return False
        else:
            return errmsg not in stderr

    def _submit_batchtask(self, scriptfile, node):
        cmd = CommandLine(
            'echo',
            environ=dict(os.environ),
            resource_monitor=False,
            terminal_output='stream',
        )
        path = os.path.dirname(scriptfile)
        qsubargs = ""
        if self._qsub_args:
            qsubargs = self._qsub_args
        if "qsub_args" in node.plugin_args:
            if "overwrite" in node.plugin_args and node.plugin_args["overwrite"]:
                qsubargs = node.plugin_args["qsub_args"]
            else:
                qsubargs += " " + node.plugin_args["qsub_args"]
        if "-o" not in qsubargs:
            qsubargs = f"{qsubargs} -o {path}"
        if "-e" not in qsubargs:
            qsubargs = f"{qsubargs} -e {path}"
        if node._hierarchy:
            jobname = ".".join((dict(os.environ)["LOGNAME"], node._hierarchy, node._id))
        else:
            jobname = ".".join((dict(os.environ)["LOGNAME"], node._id))
        jobnameitems = jobname.split(".")
        jobnameitems.reverse()
        jobname = ".".join(jobnameitems)
        jobname = jobname[0 : self._max_jobname_len]
<<<<<<< HEAD

        py_filename, file_extension = os.path.splitext(scriptfile)
        py_filename = py_filename.replace('batchscript_', '')
        py_filename = py_filename + '.py'

        cmd.inputs.args = ' "/home/predatt/giaald/.conda/envs/giacomo/bin/python %s" | qsub %s -N %s' % (py_filename, qsubargs, jobname)
=======
        cmd.inputs.args = f"{qsubargs} -N {jobname} {scriptfile}"
>>>>>>> 4d1352ade7171fd5f55eff62cee4c99a4f9cfed1

        oldlevel = iflogger.level
        iflogger.setLevel(logging.getLevelName("CRITICAL"))
        tries = 0
        while True:
            try:
                result = cmd.run()
            except Exception as e:
                if tries < self._max_tries:
                    tries += 1
                    # sleep 2 seconds and try again.
                    sleep(self._retry_timeout)
                else:
                    iflogger.setLevel(oldlevel)
                    raise RuntimeError(
                        f"Could not submit pbs task for node {node._id}\n{e}"
                    )
            else:
                break
        iflogger.setLevel(oldlevel)
        # retrieve pbs taskid
        taskid = result.runtime.stdout.split(".")[0]
        self._pending[taskid] = node.output_dir()
        logger.debug(f"submitted pbs task: {taskid} for node {node._id}")

        return taskid
