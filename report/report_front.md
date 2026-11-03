---
title: "Geometric Coordination and Residual Reinforcement Learning for Robust Bimanual Handover"
subtitle: "CSCI 645 Robot Manipulation, Fall 2026 — Final Project Report"
author: "Yan Wen"
date: "November 2026"
---

## Abstract

We study whether explicit geometric coordination and a bounded learned position residual make a simulated
two-arm handover more robust to initial-position and release-timing errors. Two Franka Panda arms with
parallel-jaw grippers hand over a rigid bar in Isaac Sim 6.2 through Isaac Lab 3.0 (PhysX backend). A
receiver follows a fixed nominal trajectory; a training-free geometry module adds a bounded object-relative
target correction, shared-holding anchoring and contact-gated release; a PPO policy adds a bounded
(2 cm per axis) Cartesian residual to the receiver target. We compare five methods — nominal, geometry,
residual, combined and combined without the explicit contact-phase observation — trained with three seeds
each for 10M environment transitions under a protocol frozen before the final runs, and evaluate all of
them on the same 1,800 held-out cases in nine conditions (19,800 episodes). Success requires two seconds of
receiver-only holding. The geometry module is decisive: it raises success on the stress
conditions from 47.8 % (nominal) to 93.3 % and on in-range conditions from 95.5 % to 100 %, and removes all
drops by delaying release until the receiver holds the bar. Trained residual policies reach 100 % in-range
and improve the nominal controller's stress success by 7.9 points, but added to geometry they bring no gain
(primary analysis: +1.2 points, 95 % CI [-4.3, +5.4]; trained final checkpoints: -3.4 [-6.3, -1.1]).
Removing the explicit contact-phase input has no detectable effect. Because the validation suite comes from
the training distribution, which geometry already solves, the frozen selection rule chose the untrained
initialization for eight of the nine runs; we report this, its consequences, and a secondary analysis of
the trained final checkpoints declared before the final results were known.

## 1. Motivation

Handing an object from one arm to another fails in two characteristic ways: the receiver grasps the object
in the wrong place because the object is not where the plan expects it, or the giver lets go before the
receiver holds it. A fixed script handles neither. Two remedies are natural: an explicit geometric layer
that measures the object and gates the release on contact, and a learned residual that corrects a scripted
controller from experience. This project tests whether either, or both together, help under controlled
spatial and timing perturbations, and whether an explicit contact-phase label helps the learned residual.
A positive result was not assumed; the goal was a reproducible, fair comparison.

## 2. Related work

Frau-Alfaro et al. learn dexterous handover between two multi-finger hands with reinforcement learning in
Isaac Lab, using a dual-quaternion reward, and report 94 % success and robustness to a moving partner
[1]. Our task uses parallel-jaw grippers and a fixed nominal plan, and asks a narrower question about
correction and release gating. Residual reinforcement learning, which superimposes a learned correction on
a conventional controller, was introduced concurrently by Johannink et al. [2] and Silver et al. [3];
ManipTrans applies residual learning to transfer bimanual dexterous skills [4]. robosuite's
TwoArmHandover task [5] informed our observation and success structure, but its success test differs from
our independent two-second holding criterion. We build on Isaac Lab [6], Isaac Sim's PhysX backend, and
the RSL-RL implementation of PPO [7, 8].
