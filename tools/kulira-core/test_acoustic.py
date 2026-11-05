from kulira_core.acoustic import TonePhrase, AcousticChannel, synchrony, vocabulary_growth

def phrase(node, pitch, t=0.0): return TonePhrase(node=node, pitch_hz=pitch, start_s=t, duration_s=0.4, amplitude=0.5)

def test_channel_attenuates_with_distance():
    ch=AcousticChannel()
    near=ch.hear(phrase("A1",440), listener_xy=(0,0), source_xy=(0,0))
    far=ch.hear(phrase("A1",440), listener_xy=(10,0), source_xy=(0,0))
    assert near > far > 0

def test_nodes_cannot_hear_own_output_during_settle():
    ch=AcousticChannel(settle_s=0.5)
    assert ch.audible(phrase("A1",440,t=1.0), listener="A1", own_last_end_s=0.9) is False
    assert ch.audible(phrase("B1",440,t=1.0), listener="A1", own_last_end_s=0.9) is True

def test_synchrony_high_when_phases_align():
    assert synchrony([0.0,0.1,-0.1]) > 0.95
    assert synchrony([0.0,1.57,3.14]) < 0.4

def test_vocabulary_growth_counts_distinct_shared_phrases():
    heard=[("A1",440),("B1",440),("B1",523),("C1",523),("C1",659)]
    v=vocabulary_growth(heard)
    assert v["shared_pitches"]==2 and v["distinct"]==3
    assert v["shared"]=={"440": ["A1", "B1"], "523": ["B1", "C1"]}
