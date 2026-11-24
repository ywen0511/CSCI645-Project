# Final talk script (4 min 30 s, no Q&A)

537 words: about 4 min 08 s at 130 words per minute, which leaves 22 s of the 4 min 30 s for pauses and slide changes.

## Slide 1  (0:00–0:14, 14 s)

Hi, I'm Yan. My project asks a simple question about robot handover: where is the object in the giver's hand, and does a learned policy help the robot answer it?

## Slide 2  (0:14–0:51, 37 s)

Two Franka arms with parallel-jaw grippers hand over a bar. The receiver must grasp it, and the giver must let go only after the receiver holds it. Two errors break this. A spatial error: the bar is not where the receiver thinks, so it hits the bar end. A timing error: the giver lets go too early and the bar drops. Residual reinforcement learning is a popular fix, so I asked when a learned residual actually improves a geometric controller.

## Slide 3  (0:51–1:32, 41 s)

The controller has a training-free geometric part. It aligns the receiver to the estimated grasp point, anchors shared holding, and opens the giver only when the receiver's grasp is stable. The bar estimate comes from the giver's kinematics: a fixed grasp transform, a half-second calibration, or continuous tracking. On top, PPO can add a bounded two-centimeter correction, with or without four frames of history. I tested four kinds of uncertainty, each with a frozen protocol, fresh held-out cases, matched training, tuned constant offsets as controls, and paired bootstrap statistics.

## Slide 4  (1:32–2:12, 40 s)

First, pose and timing errors. On the weak nominal script, the residual helps a lot: from 65 to 83 percent. But geometry alone reaches 96.5, the residual on top does not improve it, and a tuned constant offset does better. That learned residual was almost a constant. The release gate also does its job: later, 37 drops in more than a hundred thousand geometry episodes. With corrupted sensing, knowing the giver's grasp transform was enough: that baseline and every learned policy on it reached 100 percent.

## Slide 5  (2:12–2:51, 39 s)

Next, I made the bar's position inside the giver's grasp unknown. With the fixed grasp transform, success at a 15-millimeter offset falls to almost zero. A half-second calibration fixes it. A matched factorial ablation isolates this: calibration alone adds 29.5 points on the mixed condition and 93 points at 15 millimeters, both far above zero. Learned residuals on top add at most one and a half points, which is not significant, and the history policy loses 31 points at an offset outside its training range.

## Slide 6  (2:51–3:46, 55 s)

A one-shot calibration assumes the grasp stays put. So I made the bar physically slide in the giver's fingers after calibration, driven by a regulated force against friction. The one-shot controller drops from 100 to 90 percent. Does memory help? No. History against the same policy without history, and history against a controller that keeps re-estimating the grasp: both intervals include zero. What helps is simpler: tracking, a four-millimeter constant, or a memoryless residual recover most of the loss, and the history policies were unstable: two of five final checkpoints collapsed. When I reversed the history, repeated the current frame, or replaced the policy with a constant, every case had the same outcome. The policies learned a bias, not memory.

## Slide 7  (3:46–4:08, 22 s)

So the decisive quantity is where the object is in the giver's hand. Estimate it explicitly and keep it fresh, gate the release on contact, and treat learned correction as a second layer that must beat a constant offset. Code, data and videos are public. Thank you.
