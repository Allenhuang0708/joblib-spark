#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Joblib spark backend is a extension for joblib, which make joblib running on spark parallelly.
"""
__version__ = '0.1.0.dev'


def register_spark():
    """
    Register spark backend into joblib.
    """
    try:
        from sklearn.externals.joblib.parallel import register_parallel_backend
        from .backend import SparkDistributedBackend
        register_parallel_backend('spark', SparkDistributedBackend)
    except ImportError:
        msg = ("To use the spark.distributed backend you must install both "
               "the `pyspark` and `cloudpickle` packages.\n\n")
        raise ImportError(msg)


__all__ = ['register_spark']