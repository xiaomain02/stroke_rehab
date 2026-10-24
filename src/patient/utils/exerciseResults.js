
const STORAGE_KEY = "patient_demo_results";

export function getExerciseResults() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (!saved) return [];

    const results = JSON.parse(saved);

    return Array.isArray(results) ? results : [];
  } catch (error) {
    console.error("Ошибка чтения результатов:", error);
    return [];
  }
}

export function saveExerciseResult({
  exerciseId,
  exerciseType,
  score,
  durationSec,
  errors = 0,
}) {
  const results = getExerciseResults();

  const result = {
    id: crypto.randomUUID(),
    exercise_id: exerciseId,
    exercise_type: exerciseType,
    score: Number(score) || 0,
    duration_sec: Number(durationSec) || 0,
    errors: Number(errors) || 0,
    created_at: new Date().toISOString(),
  };

  results.push(result);

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(results)
  );

  window.dispatchEvent(
    new Event("patient-results-updated")
  );

  return result;
}

export function getExerciseStats() {
  const results = getExerciseResults();

  if (results.length === 0) {
    return {
      total: 0,
      averageScore: 0,
      completedExercises: 0,
    };
  }

  const totalScore = results.reduce(
    (sum, result) => sum + result.score,
    0
  );

  const uniqueExercises = new Set(
    results.map((result) => result.exercise_id)
  );

  return {
    total: results.length,
    averageScore: Math.round(
      totalScore / results.length
    ),
    completedExercises: uniqueExercises.size,
  };
}
