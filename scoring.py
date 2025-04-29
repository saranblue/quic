# scoring.py

def calculate_quiz_score(questions, user_answers, time_left, category):
    score = 0
    streak = 0
    max_streak = 0

    for i, q in enumerate(questions):
        if user_answers[i] == q.get('answer'):
            score += 1
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    bonus = 0
    if category == 'Entertainment':
        if max_streak >= 3:
            bonus += 5
        if time_left > 0:
            bonus += int(time_left * 0.5)

    total_score = score * 10 + bonus
    return {
        "raw_score": score,
        "bonus": bonus,
        "total_score": total_score
    }
