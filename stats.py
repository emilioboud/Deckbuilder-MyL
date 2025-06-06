# stats.py

import math

# =============================================================================
# 1) FUNCIONES HIPERGEOMÉTRICAS BÁSICAS
# =============================================================================
def hyper_at_least_k(total_type, draw_n, k, deck_size=50):
    """
    Retorna la probabilidad de sacar >= k cartas de un tipo determinado
    en una mano de tamaño draw_n, usando distribución hipergeométrica
    sobre un deck de tamaño deck_size.
    """
    prob = 0.0
    for i in range(k, draw_n + 1):
        if i > total_type or (draw_n - i) > (deck_size - total_type):
            continue
        prob += (
            math.comb(total_type, i)
            * math.comb(deck_size - total_type, draw_n - i)
            / math.comb(deck_size, draw_n)
        )
    return prob

def hyper_at_least_one(total_type, draw_n, deck_size=50):
    """
    Retorna la probabilidad de sacar al menos 1 carta de un tipo determinado
    en una mano de tamaño draw_n, usando distribución hipergeométrica.
    """
    if total_type == 0:
        return 0.0
    return 1 - (math.comb(deck_size - total_type, draw_n) / math.comb(deck_size, draw_n))


# =============================================================================
# 2) FUNCIONES PARA “CONSISTENCIA” ACUMULADA CON MULLIGANES
# =============================================================================
def cumulative_probabilities(n_oros, n_ali2):
    """
    Dado el número de 'Oros' (n_oros) y número de aliados costo 2 (n_ali2) en el deck,
    retorna un diccionario con probabilidades para:
      - Mano inicial (8 cartas): p8_o2, p8_o3, p8_ali2
      - Después de 1 mulligan (7 cartas): p8to7_o2, p8to7_o3, p8to7_ali2
      - Después de 2 mulligans (6 cartas): p8to7to6_o2, p8to7to6_o3, p8to7to6_ali2

    Devuelve:
      {
        "p8_o2": ...,    "p8_o3": ...,    "p8_ali2": ...,
        "p8to7_o2": ..., "p8to7_o3": ..., "p8to7_ali2": ...,
        "p8to7to6_o2": ..., "p8to7to6_o3": ..., "p8to7to6_ali2": ...
      }
    """
    # Mano de 8 cartas
    p8_ali2 = hyper_at_least_one(n_ali2, 8)
    p8_o2   = hyper_at_least_k(n_oros, 8, 2)
    p8_o3   = hyper_at_least_k(n_oros, 8, 3)

    # Mano de 7 cartas (1 mulligan)
    p7_ali2 = hyper_at_least_one(n_ali2, 7)
    p7_o2   = hyper_at_least_k(n_oros, 7, 2)
    p7_o3   = hyper_at_least_k(n_oros, 7, 3)

    # Mano de 6 cartas (2 mulligans)
    p6_ali2 = hyper_at_least_one(n_ali2, 6)
    p6_o2   = hyper_at_least_k(n_oros, 6, 2)
    p6_o3   = hyper_at_least_k(n_oros, 6, 3)

    # Probabilidades acumuladas con mulligan:
    p8to7_ali2 = p8_ali2 + (1 - p8_ali2) * p7_ali2
    p8to7_o2   = p8_o2   + (1 - p8_o2)   * p7_o2
    p8to7_o3   = p8_o3   + (1 - p8_o3)   * p7_o3

    p8to7to6_ali2 = p8to7_ali2 + (1 - p8to7_ali2) * p6_ali2
    p8to7to6_o2   = p8to7_o2   + (1 - p8to7_o2)   * p6_o2
    p8to7to6_o3   = p8to7_o3   + (1 - p8to7_o3)   * p6_o3

    return {
        "p8_o2": p8_o2,
        "p8_o3": p8_o3,
        "p8_ali2": p8_ali2,
        "p8to7_o2": p8to7_o2,
        "p8to7_o3": p8to7_o3,
        "p8to7_ali2": p8to7_ali2,
        "p8to7to6_o2": p8to7to6_o2,
        "p8to7to6_o3": p8to7to6_o3,
        "p8to7to6_ali2": p8to7to6_ali2
    }
