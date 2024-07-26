# Copyright 2024 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Definition of Check class and function.
#

class Check:

    #
    # This is a singleton value for a running counter of the number of checks
    # we have created.
    #
    check_id = 0                

    def __init__(self):
        # 
        # These can to be defined by the user:
        #
        self.CLASS = ''                  # Name for the class of check we are creating.
        self.CLASS_EXCLUDE = []          # List of check classes to exclude or '*'
        self.CLASS_INCLUDE = []          # List of check classes to include or '*'
        self.DEBUG = False               # Print what check will be created. Do nothing.
        self.SYSTEM = None               # The computing system we expect to run on.
        self.MODULE_NAME = __name__      # The name of the calling module. Should be set from the caller.

    def __call__(self, cmd, expected=None, not_expected=None, where=''):
        """
        Create a test of 'cmd'. A regex describing the expected output

        :param cmd:    The command and its arguments to execute. This may include
                       shell pipes and redirections.
        :param expected: A string or [string,string]. In the first case, string
                       is a regular expression describing the expected output.
                       In the second case, the first string is the regex and the
                       second string is either 'stdout' or 'stderr', depending on 
                       where the regex should search. The default is 'stdout'.
                       If None, or missing, no search will be performed.
        :param not_expected: Similar to 'expected', but what should not be found.
        """

        def debuginfo():
            """
            To help the user, grab the line where this check was created
            from so we can include it in any error message.
            """
            from inspect import getframeinfo, stack
            caller = getframeinfo(stack()[2][0])
            return "[%s:%d]" % (caller.filename, caller.lineno)


        #
        # We intentionally increment here before the inclusion/exclusion tests
        # so that numbering stays consistent when all tests are enabled.
        #
        Check.check_id += 1

        lcl_CHECK_CLASS = ''
        if self.CLASS:
            lcl_CHECK_CLASS = f'_{self.CLASS}'

        #
        # Check if a class of tests has been explicitly included or excluded
        #
        exclude = self.CLASS_EXCLUDE
        include = self.CLASS_INCLUDE

        if exclude or include:
            if not exclude: exclude = ['*']
            if not include: include = ['*']
            
        if   '*' not in exclude:
            if self.CLASS in exclude: return
        elif '*' not in include:
            if self.CLASS not in include: return

        #
        # If where is unspecificed we can run with any feature.
        # Be forgiving if the user forgets a leading +.
        #

        if not where:
            where = '*'
        elif where[0] not in ['-', '+']:
            where = f'+{where}'

        #
        # Get out properties ready.
        #

        name                = f'Check_{Check.check_id:04}{lcl_CHECK_CLASS}'
        valid_systems       = where.split()
        valid_prog_environs = ['builtin']
        time_limit          = '2m'

        if self.DEBUG:
            print(   f"{debuginfo()} {name:25} {cmd:80} -> "
                  + (f"expected:{expected}"           if expected     is not None else '') 
                  + (f"not_expected:{not_expected}"   if not_expected is not None else '') 
                  + (f"  on  {valid_systems} with {valid_prog_environs}"))
            return


        #
        # Wait until here to do any imports so that if we are running in debug
        # mode we don't depend on the ReFrame framework being present.
        #

        import reframe as rfm
        import reframe.utility.sanity as sn
        import reframe.core.builtins as builtins

        from reframe.core.meta import make_test

        def validate(test):
            """Callback to check that we got the output we expected."""

            a,b = True,True

            expected, where = test.expected
            if expected is not None:
                where = eval(f'test.{test.expected[1]}')
                a = sn.assert_found(expected, where, 
                                    msg=f"Expected '{expected}' running '{test.cmd} {test.caller}'")

            not_expected, where = test.not_expected
            if not_expected is not None:
                where = eval(f'test.{test.not_expected[1]}')
                b = sn.assert_not_found(not_expected, where, 
                                        msg=f"Did not expect '{not_expected}' running '{test.cmd} {test.caller}'")
            return (a and b) 

        def set_command_options(test):
            """Set up the options we need to run"""
            test.executable = test.cmd

            test.expected     =     test.expected if isinstance(    test.expected, list) else [    test.expected, 'stdout']
            test.not_expected = test.not_expected if isinstance(test.not_expected, list) else [test.not_expected, 'stdout']

            test.skip_if(    test.expected[1] not in ['stdout', 'stderr'], msg=f'Location for expected is not stdout or stderr {test.caller}')
            test.skip_if(test.not_expected[1] not in ['stdout', 'stderr'], msg=f'Location for not_expected is not stdout or stderr {test.caller}')


        def check_system(test):
            """Check that the system we require is the system we are on, otherwise skip the test."""
            test.skip_if(test.current_system.name != self.SYSTEM,
                         msg = f'Required sytem {self.SYSTEM} but found {test.current_system.name}.')


        #
        # Finally, create a register the test.
        #
        t = make_test(
                name,
                (rfm.RunOnlyRegressionTest,),
                {'cmd': cmd,
                 'expected': expected,
                 'not_expected': not_expected,
                 'valid_systems': valid_systems,
                 'valid_prog_environs': valid_prog_environs,
                 'time_limit': time_limit,
                 'caller': debuginfo(),
                },
                [builtins.run_after('setup')(set_command_options),
                 builtins.run_after('setup')(check_system),
                 builtins.sanity_function(validate),
                ],
                module = self.MODULE_NAME
            )
        rfm.simple_test(t)
