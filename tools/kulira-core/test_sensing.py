from kulira_core.sensing import Reading, assess_contact

def test_same_node_two_modalities_is_moderate_not_strong():
    r=[Reading("A1","temperature_c",31.0,22.0,"temp-1"), Reading("A1","humidity_percent",60.0,45.0,"hum-1")]
    a=assess_contact(r, min_modalities=2)
    assert a["strength"]=="moderate" and a["modalities"]==["humidity_percent","temperature_c"]

def test_two_modalities_from_independent_nodes_is_strong():
    r=[Reading("A1","temperature_c",31.0,22.0,"temp-1"), Reading("B1","co2_ppm",1400,450,"co2-1")]
    a=assess_contact(r, min_modalities=2)
    assert a["strength"]=="strong" and a["independent_nodes"]==2

def test_same_node_two_modalities_not_independent_nodes():
    r=[Reading("A1","temperature_c",31.0,22.0,"temp-1"), Reading("A1","co2_ppm",1400,450,"co2-1")]
    a=assess_contact(r, min_modalities=2)
    assert a["strength"]=="moderate" and a["independent_nodes"]==1

def test_within_noise_is_no_evidence():
    r=[Reading("A1","temperature_c",22.4,22.0,"s1")]
    a=assess_contact(r, min_modalities=1)
    assert a["strength"]=="none"

def test_motion_suggests_disturbance_not_survivor():
    r=[Reading("A1","accel_m_s2",3.5,9.8,"s1")]
    a=assess_contact(r, min_modalities=1)
    assert a["kind_hint"]=="disturbance"

def test_duplicate_sighting_id_never_corroborates():
    # same sighting_id re-reported by another node in another modality
    # is still one sighting: it must not reach strong
    r=[Reading("K1","ir_max_c",36.0,20.0,"heat-fake"), Reading("B1","co2_ppm",1500,450,"heat-fake")]
    a=assess_contact(r, min_modalities=2)
    assert a["strength"]=="weak" and a["independent_nodes"]==1
