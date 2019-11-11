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

import cloudpickle
import warnings
from multiprocessing.pool import ThreadPool

from sklearn.externals.joblib.parallel \
    import AutoBatchingMixin, ParallelBackendBase, register_parallel_backend, SequentialBackend

from sklearn.externals.joblib._parallel_backends import SafeFunction

from pyspark.sql import SparkSession


class SparkDistributedBackend(ParallelBackendBase, AutoBatchingMixin):

    def __init__(self, **backend_args):
        super(SparkDistributedBackend, self).__init__(**backend_args)
        self._pool = None
        self._n_jobs = None
        self._spark = SparkSession \
            .builder \
            .appName("JoblibSparkBackend") \
            .getOrCreate()
        self._job_group = "joblib_spark_job"

    def effective_n_jobs(self, n_jobs):
        # maxNumConcurrentTasks() is a package private API
        max_num_concurrent_tasks = self._spark.sparkContext._jsc.sc().maxNumConcurrentTasks()
        if n_jobs > max_num_concurrent_tasks:
            n_jobs = max_num_concurrent_tasks
            warnings.warn("limit n_jobs to be maxNumConcurrentTasks in spark: " + str(n_jobs))
        return n_jobs

    def abort_everything(self, ensure_ready=True):
        # Note: There's bug existing in `sparkContext.cancelJobGroup`.
        # See https://github.com/apache/spark/pull/24898
        self._spark.sparkContext.cancelJobGroup(self._job_group)
        if ensure_ready:
            self.configure(n_jobs=self.parallel.n_jobs, parallel=self.parallel,
                           **self.parallel._backend_args)

    def terminate(self):
        # Note: There's bug existing in `sparkContext.cancelJobGroup`.
        # See https://github.com/apache/spark/pull/24898
        self._spark.sparkContext.cancelJobGroup(self._job_group)

    def configure(self, n_jobs=1, parallel=None, **backend_args):
        n_jobs = self.effective_n_jobs(n_jobs)
        self._n_jobs = n_jobs
        return n_jobs

    def _get_pool(self):
        """Lazily initialize the thread pool
        The actual pool of worker threads is only initialized at the first
        call to apply_async.
        """
        if self._pool is None:
            self._pool = ThreadPool(self._n_jobs)
        return self._pool

    def apply_async(self, func, callback=None):
        # Note the `func` args is a batch here. (BatchedCalls type)
        # See joblib.parallel.Parallel._dispatch
        def run_on_worker_and_fetch_result():
            # TODO: handle possible spark exception here.
            self._spark.sparkContext.setJobGroup(self._job_group, "joblib spark job")
            ser_res = self._spark.sparkContext.parallelize([0], 1) \
                .map(lambda _: cloudpickle.dumps(func())) \
                .first()
            return cloudpickle.loads(ser_res)

        return self._get_pool().apply_async(
            SafeFunction(run_on_worker_and_fetch_result),
            callback=callback
        )

    def get_nested_backend(self):
        """Backend instance to be used by nested Parallel calls.
           For nested backend, always use `SequentialBackend`
        """
        nesting_level = getattr(self, 'nesting_level', 0) + 1
        return SequentialBackend(nesting_level=nesting_level), None