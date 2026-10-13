#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2022 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    lfric_atm.py

DESCRIPTION
    Atmosphere post processing application

ENVIRONMENT VARIABLES
  Standard Cylc environment:
    CYLC_SUITE_WORK_DIR
    CYLC_TASK_CYCLE_POINT
'''

import os
import re

from collections import OrderedDict

import modeltemplate as mt
import control
import utils
import nlist
import validation
import housekeeping
import atmos_transform as transform
import suite
import climatemean
import timer

from netcdf_filenames import NCF_TEMPLATE

MONTHS = tuple(m[:3].lower() for m in climatemean.MONTHS)
SEASONS = tuple(''.join([c[0] for c in [MONTHS[m],
                                        MONTHS[(m + 1) % 12],
                                        MONTHS[(m + 2) % 12]]])
                for m in range(12))


class LfricPostProc(mt.ModelTemplate):
    '''
    Methods and properties specific to the LFRic Atmosphere
    post processing application.
    '''
    @timer.run_timer
    def move_to_share(self,pattern=None):
        '''
        Move files to share directory
        '''
        utils.log_msg('Congratulations! You have made it into the move_to_share bit of code.', level='INFO')
        
        print("In move_to_share (LFRic)")
        print("LFRic Pattern-pre: ",pattern)
        super(LfricPostProc, self).move_to_share(pattern=pattern)
        print("LFRic Pattern-post: ",pattern)
        utils.log_msg('Congratulations! You have made it into the move_to_share bit of code, part 2.', level='INFO')
        current_date = utils.CylcCycle().startcycle['iso'][0:8]
        utils.log_msg('Our current date is '+current_date, level='INFO')

    @property
    def _mean_fields(self):
        ''' Return a list of means fields available '''
        print("In mean_fields (LFRic)")
        fields = []
        for val in self.model_components.values():
            fields += [f for f in val if 'shelf' not in f]
        print("Fields list: ", fields)
        return sorted(fields)

    def rebuild_restarts(self):
        '''Rebuild partial restart files'''
        print("Inside lfric_atm rebuild_restarts()")
        print("self.rsttypes: ", self.rsttypes)
        for rst in self.rsttypes:
            pattern = self.rst_set_stencil(rst).rstrip('$').lstrip('^')
            self.rebuild_fileset(self.share, pattern)

    @property
    def model_components(self):
        '''Name of model component, to be used as a prefix to archived files '''
        print("Inside lfric_atm model_components()")
        print("Will return: 'lfric_atm': ['mesh']")
        return {
            'lfric_atm': ['mesh']
            }

    def rsttypes(self):
        ''' Returns a tuple of restart file types available '''
        print("Inside lfric_atm rsttypes()")
        return (('', 'TESTING_0'), ('', ''), ('', 'TESTING_2'), ('', 'TESTING_3'))

    def rst_set_stencil(self, rsttype):
        '''
        Return a regular expression to match restart filenames output
        directly by the model.
        '''
        return r'^{P}a_{T1}_?\d{{8}}_restart{T2}(\.nc)?$'.format(P=self.prefix,
                                                                 T1=rsttype[0],
                                                                 T2=rsttype[1])
    
    def general_mean_stencil(self, field, base=None):
        '''
        Return the LFRic monthly mean file
        '''
        print("Inside general_mean_stencil():")
        print("self.prefix: ",self.prefix)
        print("Base: ", base)
        
        return \
         r'^{P}a_{B}(_\d{{8,10}}){{2}}_{F}(_\d{{4}})?(\.nc)?$'.format(P=self.prefix,
                                                    B=base if base else r'\d+[hdmsy]',
                                                    F=field)

    def model_realm(self, field):
        '''
        Return the standard realm ID character for the model according
        to the field argument: <type str>
            "a"    = individual atmosphere field
        Arguments:
            field <type str> Individual fieldname
                             or  "|" separated list of fieldnames
        '''
        print("In model_realm():")

        realm = 'a'
        print("realm: ", realm)
        
        return realm


    def create_means(self):
        '''
        Create monthly, seasonal, annual means.
        Delete component files as necessary.
        '''
        print("In create_means():")
        utils.create_dir(self.diagsdir)
        print("self.mean_fields:")
        print(self.mean_fields)
        for inputs in self.loop_inputs(self.mean_fields):

            # Loop over set of means which it should be possible to create
            # from files available.
            for setend in self.periodfiles(inputs, 'end'):
                period = inputs.base
                inputs.start_date = self.get_date(setend)
                meanset = self.periodfiles(inputs, 'set')
                print("meanset:")
                print(meanset)
                self.preprocess_meanset(meanset)

                # Reset start date to beginning of the period for mean_stencil
                inputs.start_date = self.get_date(sorted(meanset)[0])

                pmean = self.requested_means[period]
                print("pmean:")
                print(pmean)
                pmean.component_files = meanset
                pmean.periodend = self.get_date(setend, enddate=True)
                pmean.set_filename(self.mean_stencil(inputs), self.share)
                print("pmean:")
                print(pmean)
                if inputs.custom:
                    pmean.set_title(prefix=inputs.custom)

                cmd = ' '.join([self.means_cmd,
                                ' '.join(meanset),
                                pmean.fname['file']])
                rcode = climatemean.create_mean(pmean, cmd,
                                                self.suite.initpoint)
                if rcode == 0:
                    if os.path.exists(pmean.fname['full']):
                        # Meaning gets the time_bounds variables wrong
                        # so correct them here
                        self.fix_mean_time(utils.add_path(meanset, self.share),
                                           pmean.fname['full'])

                    if period != pmean.component:
                        print("period:")
                        print(period)
                        print("pmean.component:")
                        print(pmean.component)
                        print("self.additional_means:")
                        print(self.additional_means)
                        print("list(self.requested_means.keys())[0]:")
                        print(list(self.requested_means.keys())[0])
                        # Either archive or delete base mean components
                        if period == list(self.requested_means.keys())[0] and \
                                pmean.component not in self.additional_means:
                            msg = 'Deleting component means for '
                            utils.log_msg(msg + pmean.fname['file'])
                            utils.remove_files(meanset, path=self.share)
                        else:
                            # Move component files to `archive_ready` directory
                            msg = 'Moving component means to archive_ready for '
                            utils.log_msg(msg + pmean.fname['file'])
                            utils.move_files(meanset, self.diagsdir,
                                             originpath=self.share)


INSTANCE = ('lfricpp.nl', LfricPostProc)


if __name__ == '__main__':
    pass


