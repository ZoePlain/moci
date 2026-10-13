#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015-2017 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    lfric_atm_namelist.py

DESCRIPTION
    Default namelists for LFRIC atmospheric post processing control
'''
import template_namelist


class TopLevel(template_namelist.TopLevel):
    ''' Default values for lfric_atm_pp namelist '''


class Processing(template_namelist.Processing):
    ''' Default values for lfric_atm_processing namelist '''

    means_cmd = '/home/users/dan.copsey/fortran/mean_lfric/mean_lfric.exe'
    cat_daily_means = False


class Archiving(template_namelist.Archiving):
    ''' Default values for lfric_atm_archiving namelist '''


NAMELISTS = {'lfric_atm_pp': TopLevel,
             'lfric_atm_processing': Processing,
             'lfric_atm_archiving': Archiving}
