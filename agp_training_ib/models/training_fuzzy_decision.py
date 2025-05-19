import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

def evaluate_training_effectiveness(avg_score):
    avg_score_var = ctrl.Antecedent(np.arange(1, 6, 1), 'avg_score')

    effectiveness = ctrl.Consequent(np.arange(0, 101, 1), 'effectiveness')

    avg_score_var['rendah'] = fuzz.trimf(avg_score_var.universe, [1, 1, 3])
    avg_score_var['sedang'] = fuzz.trimf(avg_score_var.universe, [2, 3, 4])
    avg_score_var['tinggi'] = fuzz.trimf(avg_score_var.universe, [3, 5, 5])

    effectiveness['gagal'] = fuzz.trimf(effectiveness.universe, [0, 0, 50])
    effectiveness['evaluasi_ulang'] = fuzz.trimf(effectiveness.universe, [40, 60, 80])
    effectiveness['berhasil'] = fuzz.trimf(effectiveness.universe, [70, 100, 100])

    rule1 = ctrl.Rule(avg_score_var['rendah'], effectiveness['gagal'])
    rule2 = ctrl.Rule(avg_score_var['sedang'], effectiveness['evaluasi_ulang'])
    rule3 = ctrl.Rule(avg_score_var['tinggi'], effectiveness['berhasil'])

    effectiveness_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
    evaluation = ctrl.ControlSystemSimulation(effectiveness_ctrl)

    evaluation.input['avg_score'] = avg_score

    # Compute
    evaluation.compute()

    return evaluation.output['effectiveness']