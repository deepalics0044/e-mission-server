import emission.core.get_database as edb
import emission.core.wrapper.pipelinestate as ps
import emission.net.usercache.abstract_usercache as enua
import time

def mark_usercache_done(user_id):
    mark_stage_done(user_id, ps.PipelineStages.USERCACHE)

def get_time_range_for_usercache(user_id):
    get_time_range_for_stage(user_id, ps.PipelineStages.USERCACHE)

def get_time_range_for_segmentation(user_id):
    get_time_range_for_stage(user_id, ps.PipelineStages.TRIP_SEGMENTATION)

def mark_segmentation_done(user_id):
    mark_stage_done(user_id, ps.PipelineStages.TRIP_SEGMENTATION)

def mark_segmentation_failed(user_id):
    mark_stage_failed(user_id, ps.PipelineStages.TRIP_SEGMENTATION)

def get_time_range_for_sectioning(user_id):
    # Returns the time range for the trips that have not yet been converted into sections.
    # Note that this is a query against the trip database, so we cannot search using the
    # "write_ts" query. Instead, we change the query to be against the trip's end_ts
    tq = get_time_range_for_stage(user_id, ps.PipelineStages.SECTION_SEGMENTATION)
    tq.timeType = "end_ts"
    return tq

def mark_sectioning_done(user_id):
    mark_stage_done(user_id, ps.PipelineStages.SECTION_SEGMENTATION)

def mark_sectioning_failed(user_id):
    mark_stage_failed(user_id, ps.PipelineStages.SECTION_SEGMENTATION)

def get_time_range_for_smoothing(user_id):
    # Returns the time range for the trips that have not yet been converted into sections.
    # Note that this is a query against the trip database, so we cannot search using the
    # "write_ts" query. Instead, we change the query to be against the trip's end_ts
    tq = get_time_range_for_stage(user_id, ps.PipelineStages.JUMP_SMOOTHING)
    tq.timeType = "end_ts"
    return tq

def mark_smoothing_done(user_id):
    mark_stage_done(user_id, ps.PipelineStages.JUMP_SMOOTHING)

def mark_smoothing_failed(user_id):
    mark_stage_failed(user_id, ps.PipelineStages.JUMP_SMOOTHING)


def mark_stage_done(user_id, stage):
    # We move failed entries to the error timeseries. So usercache runs never fail.
    curr_state = get_current_state(user_id, stage)
    assert(curr_state is not None)
    assert(curr_state.curr_run_ts is not None)
    curr_state.last_ts_run = curr_state.curr_run_ts
    curr_state.curr_run_ts = None
    edb.get_pipeline_state_db().save(curr_state)

def mark_stage_failed(user_id, stage):
    curr_state = get_current_state(user_id, stage)
    assert(curr_state is not None)
    assert(curr_state.curr_run_ts is not None)
    # last_ts_run remains unchanged since this run did not succeed
    # the next query will start from the start_ts of this run
    # we also reset the curr_run_ts to indicate that we are not currently running
    curr_state.curr_run_ts = None
    edb.get_pipeline_state_db().save(curr_state)

def get_time_range_for_stage(user_id, stage):
    """
    Returns the start ts and the end ts of the entries in the stage
    """
    curr_state = get_current_state(user_id, stage)

    if curr_state is None:
        start_ts = None
        curr_state = ps.PipelineState()
        curr_state.user_id = user_id
        curr_state.pipeline_stage = stage
        curr_state.curr_run_ts = None
        curr_state.last_ts_run = None
    else:
        start_ts = curr_state.last_ts_run

    assert(curr_state.curr_run_ts is None)

    end_ts = time.time() - 5 # Let's pick a point 5 secs in the past to avoid race conditions

    ret_query = enua.UserCache.TimeQuery("write_ts", start_ts, end_ts)

    curr_state.curr_run_ts = end_ts
    edb.get_pipeline_state_db().save(curr_state)
    return ret_query

def get_current_state(user_id, stage):
    curr_state_doc = edb.get_pipeline_state_db().find_one({"user_id": user_id,
                                                            "pipeline_stage": stage.value})
    if curr_state_doc is not None:
        return ps.PipelineState(curr_state_doc)
    else:
        return None

