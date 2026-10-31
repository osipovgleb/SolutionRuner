"""Content-selected parent methods for the common work-rate rule."""

from .work_crew_proof import proof as crews
from .work_gap_proof import proof as gap
from .work_pair_proof import pumps
from .work_ratio_proof import apprentice, ratio_workers
from .work_remaining_proof import joining, known, measured
from .work_sum_proof import proof as summed
from .work_task_proof import integer_solver, test_count
from .work_tile_proof import proof as tile

PROOFS = {
    "work_pairs_pumps": pumps,
    "work_test_count": test_count,
    "work_tile": tile,
    "work_crews": crews,
    "work_integer_solver": integer_solver,
    "work_equal_join": joining,
    "work_sum_two": summed,
    "work_sum_three": summed,
    "work_measured_sum": measured,
    "work_known_girl": known,
    "work_known_pipe": known,
    "work_gap_pipes": gap,
    "work_gap_filter": gap,
    "work_gap_printer": gap,
    "work_ratio_workers": ratio_workers,
    "work_apprentice": apprentice,
}
