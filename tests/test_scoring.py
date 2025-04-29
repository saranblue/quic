# tests/test_scoring.py

import unittest
from scoring import calculate_quiz_score

class TestScoringLogic(unittest.TestCase):

    def setUp(self):
        self.questions = [
            {"question": "Q1", "answer": "A"},
            {"question": "Q2", "answer": "B"},
            {"question": "Q3", "answer": "C"},
            {"question": "Q4", "answer": "D"},
        ]

    def test_all_correct_answers(self):
        result = calculate_quiz_score(self.questions, ["A", "B", "C", "D"], time_left=20, category="Entertainment")
        self.assertEqual(result["raw_score"], 4)
        self.assertEqual(result["bonus"], 15)  # 5 for streak, 10 for time
        self.assertEqual(result["total_score"], 55)

    def test_some_wrong_answers(self):
        result = calculate_quiz_score(self.questions, ["A", "X", "C", "X"], time_left=10, category="Entertainment")
        self.assertEqual(result["raw_score"], 2)
        self.assertEqual(result["bonus"], 5)  # only time bonus
        self.assertEqual(result["total_score"], 25)

    def test_no_bonus_category(self):
        result = calculate_quiz_score(self.questions, ["A", "B", "C", "D"], time_left=30, category="Science")
        self.assertEqual(result["bonus"], 0)
        self.assertEqual(result["total_score"], 40)

if __name__ == '__main__':
    unittest.main()
