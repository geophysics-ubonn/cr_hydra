#!/usr/bin/env python
import os

from crh_add import crh_add
from crh_wait_to_finish import crh_wait_for_all_sims_to_finish

os.chdir('test00')
crh_add()
crh_wait_for_all_sims_to_finish()
print('Finished the inversions')
