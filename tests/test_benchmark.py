import unittest
from gesture_control.benchmark import summarize, compare


class BenchmarkTests(unittest.TestCase):
    def test_summary_uses_measured_time_and_detection_count(self):
        row = summarize([10, 20, 30, 40], 2, .2)
        self.assertEqual(row['mean_inference_ms'], 25)
        self.assertEqual(row['p95_inference_ms'], 40)
        self.assertEqual(row['processing_fps'], 20)
        self.assertEqual(row['detection_rate_percent'], 50)

    def test_comparison_computes_speedup_and_latency_reduction(self):
        result = compare({'mean_inference_ms': 40}, {'mean_inference_ms': 20})
        self.assertEqual(result['inference_speedup'], 2)
        self.assertEqual(result['inference_latency_reduction_percent'], 50)

    def test_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize([], 0, 1)

    def test_slower_gpu_is_reported_without_claiming_improvement(self):
        result = compare({'mean_inference_ms': 20}, {'mean_inference_ms': 40})
        self.assertEqual(result['inference_speedup'], .5)
        self.assertEqual(result['inference_latency_reduction_percent'], -100)
