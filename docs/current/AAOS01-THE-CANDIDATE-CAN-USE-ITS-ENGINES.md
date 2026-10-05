# AAOS-01: the candidate's own interpreter can use the engines its workers need

## 1. The test

The receipt leaves one item undone: no candidate was restaged with dependencies and the pdf and image
capabilities rerun inside it. Last round I populated the candidate's packages and recorded that I had not yet
run anything. This round asks the cheapest decisive question first: can the candidate's own interpreter
import the engines its workers need?

I ran the candidate's interpreter in isolated mode, so it could not fall back on anything outside itself.

## 2. Result

| engine | version | why it matters |
| --- | --- | --- |
| pymupdf / fitz | 1.28.2 | the PDF engine the receipt said was absent |
| PIL | 12.3.0 | image handling for the OCR path |
| pytesseract | 0.3.13 | OCR wrapper |
| markitdown | 0.1.6 | document conversion |
| trafilatura | 2.1.0 | web extraction |
| onnxruntime | 1.20.1 | inference runtime |

All imported, exit code zero, and the reported prefix and executable are the candidate's own runtime. So the
packages are genuinely inside the candidate rather than inherited from a system interpreter. That was exactly
the condition the receipt described as missing.

## 3. One real detail worth recording

Importing fitz prints its own deprecation notice: the fitz API is deprecated and will be removed in future,
and pymupdf should be imported instead. The declared dependency is pymupdf, so the requirement names the
right thing, and the import still works through the old alias. Recording it because a worker written against
the deprecated name will keep working until the library removes it, and then will not.

I am not treating this as a defect. It is a deprecation notice from the library itself.

## 4. What this establishes and what it does not

Established: the candidate now carries the engines, and its own interpreter can load them in isolation. So the
half of the undone item that was about missing dependencies is addressed.

Not established: that pdf.extract and image.ocr actually produce readable output inside this candidate. That
requires running the capabilities through the core with the worker profile, and it has not been done.
Importing an engine is not the same as it working end to end.

## 5. State

| piece | state |
| --- | --- |
| candidate layout | complete: core, data, runtime, shared, workers, manifest, profile |
| route declarations | all thirteen present and matching the single-source manifest |
| dependencies | present and importable in isolation |
| capability run through the core | NOT RUN |

## 6. What changed this round

Nothing but this document and a probe script under project-local.
No repository source file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
