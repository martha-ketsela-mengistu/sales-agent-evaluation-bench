# Synthesis Memo — Reference-Free Preference Optimization: ORPO and SimPO
**Hong, Lee & Thorne (EMNLP 2024) + Meng, Xia & Chen (NeurIPS 2024)**
**Written:** 2026-04-30 | **Author:** Martha Ketsela Mengistu

---

## Paper Summaries

**ORPO (Hong, Lee, and Thorne, EMNLP 2024)** eliminates the reference model entirely by incorporating a preference signal directly into the SFT loss. Rather than a separate preference-training stage on top of a supervised fine-tuned model, ORPO trains the model in a single pass using a composite objective: a standard SFT cross-entropy term on chosen outputs, plus an odds-ratio penalty on rejected outputs. The odds-ratio term penalizes the model for increasing the likelihood of rejected outputs relative to chosen outputs — without needing a reference model's log-probabilities. Their benchmark results show ORPO matches or exceeds DPO on AlpacaEval and MT-Bench while halving peak VRAM usage.

**SimPO (Meng, Xia, and Chen, NeurIPS 2024)** keeps the DPO loss structure but replaces the reference log-probability ratio with a length-normalized log-probability. The intuition: rather than comparing policy and reference log-probabilities, SimPO asks which output has higher average log-probability per token — a quantity computable from the policy alone. A margin term γ is added to enforce a minimum gap between chosen and rejected likelihoods. SimPO matches or exceeds DPO on HelpSteer and UltraFeedback benchmarks and outperforms ORPO in calibration on preference tasks where output length varies substantially.

---

## Path Selection Justification: ORPO as Primary, SimPO as Ablation

**Why ORPO:** ORPO's single-pass training is the right match for the Tenacious judge task. The judge is trained on binary constraint satisfaction (pass/fail on Tenacious rubric), not on nuanced quality ranking. ORPO's odds-ratio term directly penalizes constraint-violating outputs relative to constraint-passing outputs — this is exactly the objective. The single-pass design also means no separate SFT pre-training stage is needed before preference alignment, which saves a training run and simplifies the pipeline.

**Why SimPO as ablation, not primary:** SimPO's length-normalization is optimal when preferred outputs are systematically longer or shorter than rejected outputs. For Tenacious-Bench, the length distribution between chosen and rejected outputs does not have a systematic bias — both passing and failing outputs range from 80–200 words. The margin term γ also introduces a hyperparameter that requires tuning; ORPO avoids this with the fixed log-odds weighting. If ORPO achieves dev-set kappa ≥ 0.80 after 200 training steps, SimPO is unnecessary. If ORPO underfits (kappa stagnates below 0.75 at 200 steps), SimPO with γ = 0.5 will be run as ablation.

---

## Specific Disagreement: ORPO's Combined Loss Creates a Coupling Problem for Constraint Tasks

ORPO's strength — combining SFT and preference objectives in one pass — is also its limitation for a judge trained specifically on constraint violations.

The SFT term in ORPO maximizes the log-probability of chosen outputs. This is correct when chosen outputs are high-quality exemplars that the judge should learn to rate highly. But for the Tenacious judge trained as a *critic*, the chosen output is not an output the model should learn to generate — it is an output the model should learn to score as acceptable. These are different objectives. ORPO's SFT component pushes the model to be a better *generator* of chosen-style text, which is not what a post-generation filter should learn.

**Evidence from Week 10:** Trace `1fa7b6b7eff362232c14da5f7bf80f51` shows that the Week 10 generator already produces passing outputs on easy variants — the generator is not the bottleneck. Training the judge with an SFT component on passing outputs risks making the model better at generating Tenacious-style emails, which is orthogonal to the goal of teaching it to detect when a completed output violates a constraint.

**The DPO comparison highlights this.** DPO (and SimPO) use only a preference loss with no SFT component, which avoids the generation-capacity coupling. A model trained with pure DPO/SimPO on (chosen, rejected) pairs learns a scoring function, not a generation function — closer to the intended judge role.

**Implication for training data:** ORPO's SFT coupling is less harmful if the training pairs are framed as *reranking* rather than generation: the model receives the full context (prospect brief, candidate output) and outputs a binary label rather than a continuation. In the judge framing, the "chosen" output is not a text to generate but an evaluation to prefer. Whether ORPO's SFT term degrades judge calibration in this framing relative to SimPO's pure-preference objective is the key question the ablation should answer.

**Design decision:** ORPO is used as primary because its compute advantage is significant at T4 scale and the generation-coupling concern is partially mitigated by framing inputs as classification tasks. If ORPO's dev-set kappa falls below 0.75 at checkpoint 200, SimPO will be substituted. The ablation table will report ORPO vs. SimPO calibration on the dev partition.

---

## Implication for Preference Pair Construction

SimPO's length normalization creates an implicit incentive: the model is rewarded for generating shorter outputs when both length and quality are confounded in the preference signal. For Tenacious-Bench constraint detection, this is irrelevant to generation but relevant to *scoring*: a judge that internally represents constraint satisfaction as a log-probability-based score would benefit from normalized length. Whether length normalization improves binary constraint detection (pass/fail) versus nuanced quality scoring is unresolved in either paper and should be monitored in the ablation.

---

## References

Hong, J., Lee, N., & Thorne, J. (2024). ORPO: Monolithic Preference Optimization without Reference Model. *EMNLP 2024*. arXiv:2403.07691.

Meng, Y., Xia, M., & Chen, D. (2024). SimPO: Simple Preference Optimization with a Reference-Free Reward. *NeurIPS 2024*. arXiv:2405.14734.
