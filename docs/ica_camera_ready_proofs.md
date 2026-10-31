# Proof notes for "Exact Audits of Boundary Sensitivity in Step-Level Agent Evaluation"

These notes accompany the camera-ready manuscript and give the proof details compressed in the six-page paper.

## Theorem 1: universal ranking characterization

Let primitive scores lie in {0,...,K}. For a nonempty contiguous block B of length m, let S(B) be its primitive-score sum. A block-local scorer s induces the equal-call score

M_s(v;P) = (1/G) sum_{B in P} s(B).

Assume singleton scoring is nondegenerate and affine on the declared primitive scale:

s((v)) = alpha v + beta, alpha > 0.

Call M_s universally rank-invariant when, for every pair of equal-length traces x,y and every two common contiguous partitions P,Q,

sign(M_s(x;P)-M_s(y;P)) = sign(M_s(x;Q)-M_s(y;Q)).

### Sufficiency

Suppose every block B satisfies

s(B) = alpha S(B) + b_|B|,

where b_m depends only on block length. For a common partition P=(B_1,...,B_G),

M_s(x;P)-M_s(y;P)
= (alpha/G) [S(x)-S(y)]
  + (1/G) sum_g [b_|B_g|-b_|B_g|]
= (alpha/G)[S(x)-S(y)].

Since alpha/G > 0, the sign depends only on total primitive score and is independent of the common partition. Hence every weak order is preserved.

### Necessity

Under the singleton partition, equal-length traces are ordered exactly by total primitive score because singleton scoring is alpha v + beta with alpha>0.

Fix a block length m. Any two length-m blocks with the same attainable total c must tie under the singleton partition. Universal rank invariance forces them to tie under the one-block partition as well. Therefore the block score depends only on length and total:

s(B)=g_m(S(B))

for some function g_m on {0,...,mK}.

Now take two block lengths m,n and attainable totals c,d with c<mK and d<nK. Construct two equal-length traces partitioned into an m-block and an n-block, with block totals (c+1,d) and (c,d+1). Their total primitive scores are equal, so the singleton partition ties them. Universal rank invariance therefore forces

g_m(c+1)+g_n(d)=g_m(c)+g_n(d+1).

Thus

g_m(c+1)-g_m(c)=g_n(d+1)-g_n(d)

for every admissible choice. All attainable finite differences across all lengths are one common constant. For m=1 this constant is exactly alpha from singleton scoring. Hence

g_m(c)=alpha c+b_m,

and therefore s(B)=alpha S(B)+b_|B|.

This proves necessity.

Binary correctness is K=1. The all-correct block rule s(B)=product_i v_i is nonlinear in S(B) for any block length at least two, so it lies outside the universally ranking-safe class.

## Theorem 2: minimal mergeable state for primitive accuracy

For a binary trace y, let C(y) be the number of correct primitives and N(y) its length. Define primitive accuracy T(y)=C(y)/N(y).

Two traces u,v are continuation-equivalent when T(uw)=T(vw) for every finite continuation w.

### Sufficiency

If (C(u),N(u))=(C(v),N(v)), then after any continuation w both traces have the same updated correct count C(u)+C(w)=C(v)+C(w) and the same updated length N(u)+N(w)=N(v)+N(w). Their accuracies are therefore equal.

### Necessity

If T(u) != T(v), the empty continuation already distinguishes them.

Suppose T(u)=T(v) but (C(u),N(u)) != (C(v),N(v)). Then N(u) != N(v).

If the common accuracy is strictly below 1, append one correct primitive. The updated values

(C+1)/(N+1)

differ for distinct N at fixed original ratio C/N.

If the common accuracy is 1, append one incorrect primitive. The updated accuracies are N/(N+1), which differ for distinct N.

Thus unequal (C,N) pairs are not continuation-equivalent.

Any exact mergeable logger with summary sigma and merge operator plus must map continuation-equivalent traces to the same state; otherwise appending the same summary could force two different exact outputs from one merged state. Therefore an exact logger must distinguish every distinct (C,N) class. The pair (C,N) itself is mergeable by componentwise addition, so it is the coarsest exact state up to recoding. If N is supplied separately as metadata, C is the minimal additional state.

## Sharp identification after binary all-correct macro logging

For each logged block B retain its length n_B and all-correct bit z_B. Let

N = sum_B n_B,
P_c = sum_B n_B z_B,
F = sum_B (1-z_B).

Every passing block contributes exactly n_B correct primitives. A failing block may contain anywhere from 0 through n_B-1 correct primitives. Therefore total correct count lies between

P_c

and

N-F.

Hence primitive accuracy satisfies the sharp interval

A in [P_c/N, 1-F/N].

Sharpness follows because each failing block can realize every integer correct count from 0 through n_B-1 independently, so every integer total between the endpoints is attainable. With no distributional assumptions, the interval midpoint minimizes worst-case absolute loss and worst-case squared loss because both losses are maximized at an endpoint and the equal-distance center minimizes the larger endpoint distance.

## Exact contiguous-partition dynamic program

For binary all-correct block reward, define

b(i,j)=product_{t=i+1}^j y_t.

For exactly g blocks covering the first j primitives, with maximum block length k, define F^-(j,g) and F^+(j,g) as the minimum and maximum passing-block totals. Then

F^±(j,g)
= opt_{±, 1<=ell<=min(k,j)}
  {F^±(j-ell,g-1)+b(j-ell,j)},

with F^±(0,0)=0 and infeasible states assigned +infinity/-infinity as appropriate.

Every feasible partition has a unique final block of some admissible length ell; deleting it leaves a feasible predecessor partition, and conversely every predecessor plus an admissible final block yields a feasible partition. Induction on (j,g) proves exactness. Prefix error counts evaluate b in O(1), giving O(nGk) time and O(nG) storage; backtracking gives an attaining partition.

For a pair of policies A,B, replace b with the average block-level A-minus-B reward under the shared block. Linearity gives exact extrema of the mean pairwise margin under one common partition. A positive lower bound certifies A>B throughout the declared family; a negative upper bound certifies B>A; otherwise abstention is required.

## Theorem 3: tractability boundary

Exact optimization is polynomial for the contiguous chain family above. It becomes NP-hard for arbitrary catalog-constrained macro families even when a feasible interface is guaranteed.

Reduce from Exact Cover by 3-Sets (X3C). Given universe U and family S of 3-element subsets, create one primitive for each element of U. The macro catalog contains:

- every singleton {u}, with local reward 0;
- every listed triple S in the X3C instance, with local reward 1.

Because all singletons are available, a feasible partition is always guaranteed.

Ask whether the maximum equal-block average reward is 1. Such a score requires every chosen block to have reward 1, so the partition must consist entirely of disjoint listed triples covering every primitive exactly once. This is precisely an exact cover. Conversely, an exact cover gives a partition consisting only of reward-one triples and therefore score 1.

Thus deciding whether the optimum is 1 solves X3C, proving NP-hardness of the arbitrary-catalog optimization problem. The hardness is in optimization, not feasibility.
