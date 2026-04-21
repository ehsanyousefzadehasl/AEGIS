import datetime
import uuid

class Task:
    def __init__(self, user, dir, task):
        self.task_id = uuid.uuid4()
        self.user = user
        self.dir = dir
        self.task = task
        # when it is queued is considered as 
        self.user_submit_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.start_service_time = None
        self.finish_time = None
        self.status = "queued"
        self.finish_status = None
        self.recovered = False
        self.recovery_count = 0
        self.recovery_min_free_mib_override = None
        self.last_failure_reason = None

    def _to_string(self):
        return f"task id: {self.task_id} \nsubmitted by user: {self.user}, \ndirectory: {self.dir} \ntask: {self.task} \nrecovered?: {self.recovered}"

    def set_id(self, id):
        self.task_id = id

    def set_status(self, st):
        self.status = st

    def set_if_recovered(self):
        self.recovered = True

    def set_service_time(self, sst):
        self.start_service_time = sst
    
    def set_finish_time(self, ft):
        self.finish_time = ft

    def set_finish_status(self, fs):
        self.finish_status = fs

    def set_user_submit_time(self, ust):
        self.user_submit_time = ust

    def set_recovery_count(self, count):
        self.recovery_count = int(count)

    def increment_recovery_count(self):
        self.recovery_count += 1

    def set_recovery_min_free_mib_override(self, value):
        self.recovery_min_free_mib_override = None if value is None else int(value)

    def set_last_failure_reason(self, reason):
        self.last_failure_reason = reason

# The queue for keeping submitted tasks
class Tasks():
    def __init__(self):
        self.queue = []
 
    def enqueue(self, value):
        # Inserting to the end of the queue
        self.queue.append(value)
 
    def dequeue(self):
         # Remove the furthest element from the top,
         # since the Queue is a FIFO structure
         return self.queue.pop(0)
    
    def check(self):
        return self.queue[0]
    
    def put_it_back(self, value):
        self.queue.insert(0, value)

    # returns the number of tasks in the queue
    def length(self):
        return len(self.queue)
    
    # returns whole queue
    def whole_list(self):
        return self.queue