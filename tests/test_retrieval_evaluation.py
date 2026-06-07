import unittest

from app.schemas import RetrievalEvalCase, RetrievalEvalRequest
from app.retrieval_eval import evaluate_retrieval_cases
from app.schemas import SourceChunk


class RetrievalEvaluationTest(unittest.TestCase):
    def test_retrieval_evaluation_reports_metrics(self):
        request = RetrievalEvalRequest(
            top_k=3,
            cases=[
                RetrievalEvalCase(
                    question="RUL과 SoH는 무엇이 다른가요?",
                    expected_sources=["battery_rul_basics.md"],
                )
            ],
        )

        response = evaluate_retrieval_cases(
            request.cases,
            request.top_k,
            lambda _question, _top_k: [
                SourceChunk(source="battery_rul_basics.md", chunk_index=0, text="RUL and SoH"),
                SourceChunk(source="deployment.md", chunk_index=0, text="Deployment"),
            ],
        )

        self.assertEqual(response.total_cases, 1)
        self.assertEqual(response.hit_at_k, 1)
        self.assertEqual(response.mrr, 1)
        self.assertAlmostEqual(response.mean_precision_at_k, 0.3333)
        self.assertEqual(len(response.results), 1)


if __name__ == "__main__":
    unittest.main()
