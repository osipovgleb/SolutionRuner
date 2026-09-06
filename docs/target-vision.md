# Target vision

This document defines what a good SolutionRuner result should feel like to the
operator. It complements the mechanical safety requirements in
`runner-authoring-contract.md`: that contract says when a runner is safe, while
this document says what the repaired condition, solution, and visual assets
should look like.

The principles below were distilled from accepted and rejected results across
the existing SVG-conversion, graph, vector, polygon, and triangle tasks. They
are the default editorial policy unless the operator gives a more specific
instruction for a group.

## Desired result

A repaired child should look as though the author of the parent problem wrote
the child solution deliberately. It must not look like an unrelated generic
solution, a shortened answer key, or a mechanical search-and-replace result.

The parent is an editorial and mathematical reference, not an immutable text
blob. Preserve its intent closely; recompute the child's mathematics from the
child condition.

## Parent-faithful solution style

Preserve from the parent whenever semantically valid:

- the mathematical method;
- the order of reasoning;
- the level of explanation;
- paragraph boundaries and transitions;
- the order and vertical placement of formulas;
- notation and naming conventions;
- the order of multiple published methods;
- the placement and visual role of solution diagrams.

Reuse parent prose unchanged when it remains true for the child. Adapt only the
parts that the child's condition requires. The goal is not literal HTML
identity; the goal is a natural child-specific version of the same authored
solution.

Before rendering, classify every meaningful parent fragment as one of:

1. a mathematical step whose meaning must be preserved;
2. editorial structure whose placement or rhythm should be preserved;
3. parent-specific data that must be mapped and replaced;
4. incidental noise that must not be copied.

Incidental noise includes stray dashes, broken sentences, remnants of removed
bank tasks, duplicate answer lines, damaged markup, obsolete wording, and
labels or remarks that apply only to the parent. Presence in the parent does
not by itself make a fragment authoritative.

## Mathematical adaptation

Never replace numeric text blindly. Parse the child's condition, build an
explicit semantic map from child values and objects to parent variables,
recompute with exact arithmetic, and account for every affected formula.

Every remaining number, label, named point, and claim in the rendered solution
must be either:

- invariant across the accepted condition grammar;
- derived from the child condition; or
- explicitly introduced and justified by the solution.

If a parent fragment cannot be related to the child condition, do not copy it
silently. Fail closed for that child unless a deterministic adaptation is
available.

Existing answers and solutions are repair targets, not mathematical evidence.
The canonical answer comes from the child condition and registered rule.

## Explained deviations from the parent

The solution may depart from the parent when the child's mathematics genuinely
requires it. Keep the departure minimal and in the parent's style.

When adding multiple computations, do not emit an unexplained sequence of
formulas. The solution must make clear:

- which quantity is being found;
- why it is needed;
- which property justifies the calculation; and
- how the result feeds the next step or the requested answer.

For example, if a child first requires finding a third angle and then using it
to find the requested angle, introduce both purposes in prose rather than
placing two disconnected calculations under the copied parent text.

Internal runner checks are not automatically published solution methods. A
runner may verify an area by coordinates, Pick's theorem, and a bounding
rectangle while publishing only the method used by the parent. Publish extra
methods only when the parent contains them or the operator explicitly asks for
them.

Do not compress several vertically separated parent formulas into one
horizontal paragraph. Do not collapse an explanatory derivation into one line
merely because the final answer is correct. When a decimal must be converted to
a reduced fraction for the child's derivation, show that conversion as its own
formula step if that matches the parent's explanatory level.

Do not duplicate the final answer inside solution HTML when the platform owns a
separate answer section.

## Condition assets: reuse the parent's SVG from condition semantics

When a child has a PNG or JPEG condition image and the parent has an SVG, prefer
the exact existing parent SVG when the normalized child and parent conditions
describe the same diagram role.

Judge compatibility from the conditions, not from exhaustive inspection of the
group and not from the mere absence of text inside the SVG. Normalize visible
text and inline LaTeX, remove bank-formatting artifacts, and replace concrete
numeric values with semantic slots before comparing the mathematical
construction.

A high similarity score is only a candidate signal. Do not use a raw character
or token percentage as the final decision. A small difference in object,
relation, marked property, or requested construction can be mathematically
decisive even when most words match.

Reuse is allowed when:

- the parent and child conditions describe the same mathematical object and
  diagram role;
- differences are limited to values that are not encoded by the SVG, or to
  equivalent serialization and wording;
- every SVG label has an unambiguous counterpart in the child condition;
- every marked equality, right angle, parallel relation, or other visual claim
  is asserted by both conditions; and
- the answer does not depend on child-specific pixels absent from the text.

Letters and marks are not forbidden literally. They are allowed when their
semantics map exactly to the child condition. Conversely, an unlabeled image is
not automatically safe: a visibly isosceles triangle is not a neutral diagram
for arbitrary triangles, and an unlabeled graph with concrete extrema still
encodes task-specific data.

Positive example: group 27719, child 60757. The parent and child both describe
rhombus `ABCD`, intersection point `O`, and the scalar product of vectors along
the two diagonals. Only the diagonal lengths differ, and the lengths are not
drawn in the parent SVG. The parent's labeled SVG is therefore compatible with
the child's raster image even though it contains letters.

When reuse is proven:

- attach the exact registered parent asset;
- do not generate or upload a duplicate SVG;
- preserve an already matching child asset;
- prevent duplicate condition images; and
- verify the materialized condition with fresh readback.

When compatibility cannot be proven from the accepted condition forms, do not
guess from the picture. Leave that child unchanged and report a record-local
failure.

## Minimal research, frozen grammar, and deterministic rules

Do not analyze every child before building a runner. The normal evidence set is
the mandatory parent plus one explicitly selected repair-needed child. Read a
second child only when the first sample leaves a specific alternative form or
mapping ambiguous.

Here, `grammar` means the exact condition forms the parser can safely recognize,
not natural-language grammar. It includes the mathematical object, named
entities, relations, values to extract, equivalent LaTeX or text forms, and the
requested quantity.

Here, `rule` means the deterministic behavior after parsing: semantic mapping,
computation, canonical answer, parent-faithful solution rendering, asset reuse,
and allowed transformations.

Freeze the grammar and rule before processing the group. During a group run,
the runner must not learn new forms from batch contents, relax the parser, or
redesign itself. Each record either matches the frozen grammar or receives zero
writes and a structured local failure.

`get_problem_batch` is allowed after the grammar and record-local fail-closed
behavior are implemented and frozen. At that point it is an execution
transport, not a research corpus.

## Run, observe, refine

The intended operating loop is short and resumable:

1. Inspect the parent and one repair-needed child.
2. Inspect a second child only for a concrete unresolved ambiguity.
3. Freeze the accepted grammar, semantic mapping, computation, rendering, and
   asset policy.
4. Implement the deterministic runner and local fixtures.
5. Run the group without watching every task individually.
6. Return after a short interval and inspect the structured summary, checkpoints,
   readback results, and unique error classes.
7. Inspect only representative failed records needed to understand those error
   classes; do not re-audit successful tasks.
8. Refine the runner narrowly and resume from saved state.

Successful and freshly verified records remain complete. One unsupported child
does not invalidate or block independent children. Repeated runs must skip or
freshly confirm already-correct records rather than rewrite them blindly.

The summary should answer:

- how many records were applied, already complete, skipped, or failed;
- which unique failure classes occurred;
- whether failures were record-local or shared;
- whether fresh readback matched the computed plan; and
- whether the frozen manifest can be resumed safely.

## Visual quality

Passing numerical checks does not prove that a generated diagram or graph looks
good. When visual fidelity matters, produce a local preview and, where useful,
an overlay with the source image.

Preserve the parent's visual language: canvas composition, colors, stroke
weights, marker shapes, label style, and diagram placement. Rebuild
child-specific geometry from the child evidence: coordinates, slopes,
extrema, tangency, auxiliary lines, and labels such as `y=f(x)` versus
`y=f'(x)`.

If a result passes tests but looks worse than an accepted reference, it is not
accepted. Investigate the visual cause. Do not defend a visibly poor curve only
with a small numeric deviation. Earlier accepted visual examples are stronger
style references than a generic smoothing algorithm.

For unstable image recognition, prefer rejection to a majority vote when
different safe parameter settings produce different geometry. A warning or
record-local failure is better than a plausible but wrong diagram.

A local preview is not authorization to upload. Creating a reusable SourceAsset
and attaching it to a problem are separate production effects. If the operator
says not to upload, do not upload even an unattached candidate revision.

## Positive patterns

- Preserve a vector solution's vertical list of vectors, while recomputing all
  coordinates, sums, dot products, and lengths from the child.
- Reuse a graph prototype's visual style, while deriving its curve, tangent,
  marked points, and function label from the child.
- Preserve the parent's order of multiple methods and use a separate visual for
  each published method when that is the established presentation.
- Add a necessary fraction-reduction or intermediate-angle step with a short
  explanation of why it is needed.
- Reuse one exact parent SVG across compatible raster children rather than
  generating or uploading equivalent duplicates.

## Rejected patterns

- Copy parent HTML and change only the final answer.
- Leave an unexplained parent number, point name, formula, or image mark.
- Flatten vertically authored formulas into one horizontal block.
- Copy a prototype's slope, extrema, proportions, or geometry when only its
  style was intended as the reference.
- Publish every internal cross-check as an extra solution method.
- Treat a nonempty child solution as correct without recomputation.
- Inspect every task in a group before implementing fail-closed behavior.
- Stop the whole group because one record has an unsupported condition or bad
  stored answer.
- Claim visual success solely because tests pass.
- Upload or attach an asset after the operator requested preview-only work.

## Final self-review

Before declaring a child complete, verify:

- every published step follows from the child condition;
- every parent-specific value and label was replaced or proven invariant;
- necessary deviations are explained in the parent's style;
- incidental bank noise was not copied;
- formula order, paragraph rhythm, and visual placement remain parent-faithful;
- the answer was recomputed independently;
- any reused SVG is justified by condition semantics;
- unsupported records received zero writes without blocking later records; and
- fresh readback produces an empty deterministic repair plan.
