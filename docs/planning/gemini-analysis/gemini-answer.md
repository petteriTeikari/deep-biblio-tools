

# **Refactoring Addendum: A User-Centric and De-Risked Strategy for Deep-Biblio-Tools**

## **Introduction: From Technical Blueprint to User-Centric Solution**

This document serves as a critical addendum to the existing "Deep-Biblio-Tools" refactoring proposal. It directly addresses the strategic gaps identified in a prior technical review, which highlighted a lack of user validation, insufficient risk analysis for data complexity, an undefined AI interaction model, and the absence of an incremental delivery strategy. The original proposal outlines a technically sound architecture, but one conceived in a vacuum, isolated from the messy realities of its intended users and their data.

The core objective of this addendum is not to discard the sound technical architecture previously proposed but to ground it in reality. The plan will be augmented with the necessary product discovery, risk mitigation, and data-driven prioritization to ensure the final product delivers tangible, measurable value to its intended academic users. This document provides the strategic guardrails to shift the project's focus from building a *beautiful engine* to building the *right system* that solves real-world problems. By integrating user-centric design principles from the outset, the project can avoid creating a tool that is elegant in theory but impractical in application, ensuring the significant engineering effort results in a successful and valued product.

---

## **Part 1: Grounding the Project in User Reality: Personas and Use Cases**

A core deficiency in the initial plan was its failure to define, understand, or even acknowledge the end-user. A design process must begin with user research to build empathy and identify what users truly need from a product.1 Without this foundation, even the most technically proficient project is likely to fail. This section rectifies that omission by establishing clear user personas. These personas are not arbitrary fictions but research composites, synthesized from studies on academic software usage, researcher workflows, and the specific challenges faced by graduate students and postdoctoral researchers.3 They will serve as the "northern star" for all subsequent design and development decisions, ensuring the team remains focused on the end user and their goals.1

### **1.1 Defining the User Landscape: Primary and Secondary Personas**

To build a successful product, it is vital to understand the needs, goals, and observed behavior patterns of the target audience.1 For a specialized tool like Deep-Biblio-Tools, the user base is not monolithic. It spans a spectrum of technical skill and academic experience. Based on analyses of researcher behavior and common pain points, two key personas emerge that represent the most important user groups.3

#### **Primary Persona: "Post-doc Paula" (The Power User)**

* **Header:** Paula, 32, Postdoctoral Researcher in Computational Biology. Quote: *"My PI needs this manuscript submitted by Friday. I don't have time to manually check 150 references for formatting errors or missing DOIs."*
* **Demographics & Background:** Paula holds a PhD in a computationally intensive field. She is highly proficient with the command line, LaTeX, Git, and various scripting languages. Her professional life is defined by the competitive, "publish or perish" academic environment, where efficiency and output are paramount.7
* **Goals:** Her primary goal is to maximize research output while minimizing time spent on non-research, administrative tasks. She needs to ensure her manuscripts are of the highest quality to avoid desk rejection from top-tier journals. A critical part of this is maintaining a clean, accurate, and reusable personal bibliography database that can be leveraged across multiple projects and collaborations.
* **Frustrations & Pain Points:** Paula finds existing bibliography management tools to be clunky, slow, and insufficiently powerful for her needs. They often lack robust scripting capabilities and require significant manual intervention to clean up the "chaotic hellscape" of bibliographic data.3 Her biggest frustration stems from inconsistent metadata pulled from different sources (e.g., PubMed, arXiv, publisher websites), which creates a time-consuming "cleanup" nightmare before every submission.5 For Paula, errors in a bibliography are not just typos; they are a direct threat to her professional reputation and a waste of her most valuable resource: time.9
* **Scenario:** Paula is the lead author on a major review paper with three co-authors. She has just merged their respective .bib files into a single master file for the manuscript. The result is a mess of duplicate entries with slightly different citation keys, inconsistent author name formatting, varied title capitalization, and dozens of entries missing DOIs or page numbers. She needs a powerful, scriptable command-line tool that can be integrated into her pre-submission workflow. She wants to run a single command that will automatically deduplicate entries, fetch missing metadata from an authoritative source like CrossRef, standardize all fields, and generate a log of any ambiguities that require her final judgment.

#### **Secondary Persona: "Grad-student Greg" (The Novice User)**

* **Header:** Greg, 24, First-year PhD student in Social Sciences. Quote: *"I'm supposed to use APA 7th, but my Zotero export has errors. I'm terrified my professor will think I'm sloppy or don't know how to do research."*
* **Demographics & Background:** Greg has a Bachelor's degree and is new to the formal conventions of academic publishing. While generally tech-savvy, he finds specialized academic tools like LaTeX and BibTeX to have a steep learning curve and is often unaware of the best tools available.5 His primary field uses APA style, which has its own strict formatting rules.11
* **Goals:** Greg's immediate goal is to learn the "rules of the game" for academic writing and produce correctly formatted papers that meet his course requirements and impress his advisor. He is highly motivated to avoid looking inexperienced or careless.
* **Frustrations & Pain Points:** Greg is overwhelmed by "citation chaos"—the seemingly arbitrary and complex rules of different citation styles.9 He finds it difficult to manage the nuances of specific styles and is afraid of making "dumb mistakes" that could harm his grades or reputation.9 He frequently uses automated citation generators or export features from library databases, but these tools often produce output with subtle but critical errors (e.g., incorrect title capitalization, missing DOIs, improper use of
  et al.) that he doesn't have the expertise to spot or fix.16 The time required to learn and master these tools feels prohibitive for a time-strapped graduate student.5
* **Scenario:** Greg has exported a list of 50 references from his university's library portal for his first major literature review. The resulting .bib file is riddled with problems: some entries are missing authors, others have the journal title in all caps, and several preprints lack any kind of persistent identifier. He tries to fix them by hand but is unsure about the correct APA 7th edition format for a preprint versus a journal article. He needs a tool that is intuitive and forgiving. Ideally, it would analyze his messy file, identify the problems in plain English, and offer to fix them automatically with a single click or simple command.

### **1.2 The Psychology of Citation: Confidence as a Core Metric**

The frustrations of both Paula and Greg point to a deeper, more fundamental need that goes beyond simple error correction. A first-order analysis reveals that users find bibliography management to be a frustrating, time-consuming, and error-prone task.9 However, connecting this frustration to the high-stakes context of academic evaluation reveals a more powerful motivator: fear.

In academia, a bibliography is not merely a list of sources; it is a signal of the author's credibility and scholarly rigor.18 An error-filled reference list can be interpreted by reviewers and editors as a sign of "intellectual laziness, unclear thinking, and inaccurate writing".13 Such mistakes can "mar an author's professional reputation" and contribute to a manuscript's rejection.9 This transforms the task from a technical problem ("my BibTeX won't compile") into an emotional and professional one ("my career is on the line").

This understanding reframes the core value proposition of the Deep-Biblio-Tools project. The system's primary function is not just to be a "fixer" but to be a "validator" and, most importantly, a "confidence-builder." The ultimate goal is to provide the user with the assurance that their bibliography is correct, allowing them to submit their work without fear of their diligence being called into question.

Consequently, project success cannot be measured solely by the number of errors fixed. A crucial key performance indicator (KPI) must be a "User Confidence Score." This can be measured through post-task surveys asking users to rate their confidence in their bibliography's correctness *after* using the tool.19 The entire user experience should be designed to foster this confidence. For example, instead of silently fixing an error, the tool should provide transparent feedback: "Fixed inconsistent capitalization in title '...' to match the publisher's official record (Source: CrossRef)." This transparency transforms the tool from a black box into a trustworthy assistant.

### **1.3 The Critical "Job to be Done" (JTBD)**

Synthesizing the needs of both the power user and the novice reveals a shared, critical moment in their workflow. While long-term reference management is an ongoing task 18, the most acute pain point—the "hair-on-fire" problem—occurs in the final stages of manuscript preparation. This is the moment of highest urgency and lowest tolerance for error. This leads to the following "Job to be Done" (JTBD) statement that should guide the project's priorities:

*When I am preparing a manuscript for submission, I want to automatically validate and repair my entire bibliography against authoritative sources to eliminate errors in metadata and formatting, so I can submit my work with confidence and avoid desk rejection.*

This JTBD provides a sharp focus for development. It targets a high-value, high-urgency moment in the researcher's workflow that is common to all academic disciplines.18 While the core need for accuracy and confidence is persona-agnostic, it allows for persona-specific implementations: a powerful CLI for Paula's automated pipeline and a guided, interactive experience for Greg's one-off literature review. Most importantly, it defines a clear, measurable outcome—a verifiably correct bibliography—that directly informs the success metrics defined later in this document.

### **Table 1: User Persona Profiles**

The following table provides a scannable summary of the primary and secondary user personas. This artifact is intended to be a constant reference for the development team, ensuring that every design, engineering, and product decision is made with a clear understanding of the target users. It helps to ask, "Would this work for Paula? Would this be understandable to Greg?" 3, thereby keeping the project user-centric.1

| Attribute | "Post-doc Paula" (The Power User) | "Grad-student Greg" (The Novice User) |
| :---- | :---- | :---- |
| **Role** | Postdoctoral Researcher, Computational Biology | First-Year PhD Student, Social Sciences |
| **Quote** | *"My PI needs this manuscript submitted by Friday. I don't have time to manually check 150 references for formatting errors or missing DOIs."* | *"I'm supposed to use APA 7th, but my Zotero export has errors. I'm terrified my professor will think I'm sloppy or don't know how to do research."* |
| **Goals** | Maximize research output; minimize time on administrative tasks; ensure manuscript quality to avoid desk rejection; maintain a clean, reusable bibliography database. | Learn academic conventions; produce correctly formatted papers; meet course requirements; avoid looking inexperienced. |
| **Frustrations** | Clunky, non-scriptable tools; inconsistent metadata from different sources; time wasted on manual cleanup; high professional cost of errors. | Overwhelming citation style rules; steep learning curve for tools; subtle errors from citation generators; fear of negative judgment from professors. |
| **Technical Skills** | High proficiency with LaTeX, BibTeX, Git, command line, scripting (Python/Bash). | Competent with standard software (MS Word, Zotero) but a novice with specialized academic tools like LaTeX. |
| **Key Scenario** | Merging and cleaning a large, messy .bib file from multiple collaborators for a journal submission. Needs a powerful, automated, command-line solution. | Cleaning up a small, incomplete .bib file exported from a library database for a course paper. Needs an intuitive, guided tool that explains and fixes errors. |

---

## **Part 2: Taming the Chaos: A Deterministic Policy for Data Conflicts**

The original plan's most dangerous assumption was that fixing a bibliography is a straightforward engineering task. In reality, bibliographic data is a "chaotic hellscape" of ambiguity, inconsistency, and conflicting information. This chaos arises because the data is created and curated by a wide variety of humans and systems, stored in fragile formats like BibTeX, and aggregated by services with different standards and goals.8 A tool that fails to anticipate and manage this chaos will inevitably produce incorrect output, break user trust, and fail in its primary mission.9 This section establishes a clear, deterministic policy for identifying and resolving the most common data conflicts, providing the foundation for a robust and trustworthy system.

### **2.1 Identifying and Classifying Data Conflicts and Edge Cases**

A systematic approach to handling data issues begins with classifying the most frequent sources of error and ambiguity. Analysis of common BibTeX problems and metadata quality studies reveals three primary categories of conflict that the system must be designed to handle.23

1. **Metadata Source Discrepancy:** A single scholarly work can be described differently across various databases. CrossRef, as the official DOI registration agency, holds metadata deposited directly by publishers and is considered highly authoritative.27 It even has specific schemas to distinguish content types like preprints.29 However, a preprint on arXiv will have its own metadata record, as will the same article when indexed in PubMed or Scopus.32 These sources can and do provide conflicting information for the same article, such as different author lists, publication dates, or even slightly different titles.24 A tool that queries multiple sources without a clear hierarchy of truth will only amplify this chaos.
2. **Author Name Ambiguity:** This is one of the most common and frustrating problems in bibliography management. A single author, "John H. Smith," can appear in a .bib file in numerous formats: John H. Smith, J. H. Smith, Smith, John H., or even J.H. Smith.8 BibTeX parsers can easily misinterpret these, for example, treating "J.H." as a single first name and dropping the middle initial. Furthermore, names with non-ASCII characters (e.g.,
   Müller, García) are frequently stored without the proper LaTeX escaping (e.g., {\\"u}, \\'{a}), leading to compilation errors or incorrect rendering.23
3. **Citation Style Variation:** The original plan's most significant oversight was ignoring citation styles. A bibliography is not a monolithic format; its final presentation is governed by one of thousands of possible style guides (e.g., APA, MLA, Chicago, IEEE, Vancouver).20 Different academic disciplines mandate different styles.11 These styles dictate critical formatting rules, including:
   * **Title Capitalization:** Whether titles are rendered in "Title Case" (most words capitalized) or "sentence case" (only the first word and proper nouns capitalized).8
   * **Author Separators:** Whether the final author in a list is preceded by "and" or an ampersand (&).13
   * **Use of "et al.":** Critically, the rules for when to truncate a long author list with "et al." vary significantly between styles. APA 7th edition uses it for three or more authors 37, Chicago style for four or more 37, and older versions of APA had different rules for the first vs. subsequent citations.39 A tool that hard-codes a single rule for
     et al. is fundamentally broken for academic use.

### **2.2 An Internal, Neutral Data Representation**

Addressing the complexity of thousands of citation styles 40 with ad-hoc, style-specific logic is an unscalable and brittle approach. The core architectural problem is the conflation of

*data* (the author's name, the article's title) with its *presentation* (the final formatted string in a specific style). The BibTeX format itself often encourages this anti-pattern, for instance, by requiring users to manually protect words with double braces ({{GPU}}) to force capitalization for a particular style's output, thereby polluting the data with presentation-layer concerns.8

The solution is to decouple these concerns through a fundamental architectural decision: the refactored system must *never* operate directly on BibTeX or any other presentation-specific format. All input must be immediately parsed into a single, rich, neutral, and style-agnostic internal data representation. The established, open standard for this purpose is the **Citation Style Language JSON (CSL-JSON)** data format.42

Adopting CSL-JSON as the internal data model resolves multiple problems simultaneously and elegantly:

* **Decoupling:** It creates a clean separation between the "front end" of the system (parsing various input formats like BibTeX) and the "back end" (generating formatted output). The core logic of the tool—validation, enrichment, and conflict resolution—will operate *only* on CSL-JSON objects.
* **Scalability:** It makes supporting any new citation style a trivial matter. Instead of writing new code, the system simply applies a different CSL style file (.csl) at the very end of the process. This is accomplished using a standard, off-the-shelf CSL processor like citeproc-js, which handles the complex logic of interpreting the style rules.44
* **Elegant Problem Solving:** It provides a definitive solution to the et al. problem. The internal CSL-JSON object will *always* store the complete list of all authors for a work. The decision of when and how to truncate this list is delegated entirely to the CSL style file, which contains the precise rules for the target style (e.g., APA 7's "3 or more" rule vs. Chicago's "4 or more" rule).37 The core tool logic no longer needs to be aware of these variations.

### **2.3 Deterministic Resolution Policies**

To build user trust and enable predictable AI behavior, the system's actions must be deterministic. When faced with ambiguity, it will follow a clear, documented hierarchy of rules. The guiding principle is to prefer making a verifiable correction and logging a transparent warning over failing silently or making an untraceable guess.

* **Policy 1: Metadata Source Hierarchy**
  * **Rule:** For any given DOI, the metadata record from **CrossRef** is considered the primary source of truth for core bibliographic fields (authors, title, publication venue, year, pages). As the official DOI registration agency, its data is deposited directly by publishers and is the most canonical source available.27
  * **Procedure:** When validating or enriching an entry, the system will first query the CrossRef REST API.27 If other linked identifiers (e.g., an arXiv ID) provide conflicting data, the system will default to using the CrossRef version. However, to ensure transparency for power users like Paula, it will log a
    ConflictWarning that details the discrepancy (e.g., ConflictWarning: Author list for DOI 10.1234/journal.5678 differs between CrossRef and arXiv:2401.0001. Using CrossRef version.).
* **Policy 2: Author Name Normalization**
  * **Rule:** All author names will be parsed and stored internally using the structured CSL-JSON format, which provides distinct fields for family, given, dropping-particle, non-dropping-particle, and suffix.46
  * **Procedure:** The system's parser will be designed to robustly handle common variations (e.g., Smith, J. H. and J. H. Smith) and convert them into the identical structured object. It will standardize initials (e.g., J.H. becomes J. H.) to prevent misinterpretation by style processors.8 This clean, structured data is then passed to the CSL processor, which can correctly format the name according to any target style's rules (e.g.,
    Smith, J. H. or J. H. Smith).
* **Policy 3: Style-Agnostic Correction and Rendering**
  * **Rule:** The core fixing and validation logic will not perform any style-specific transformations. It will operate purely on the CSL-JSON data model.
  * **Procedure:** All style-dependent formatting—including title casing, et al. truncation, author separators, and punctuation—will be handled exclusively by applying a user-selected CSL style file during the final output generation stage. The tool will be distributed with a library of the most common CSL styles (e.g., apa.csl, ieee.csl, modern-language-association.csl, chicago-author-date.csl) sourced from the official, community-maintained Zotero Style Repository, which contains over 10,000 styles.41 This makes the tool exceptionally flexible and future-proof.

### **Table 2: Data Conflict Resolution Policies**

This table provides a clear, unambiguous reference for developers and advanced users on how the system will behave in messy, real-world situations. It embodies the deterministic principles outlined above and is crucial for building a predictable and trustworthy tool.

| Conflict Type | Example of Messy Data (in .bib file) | Internal Representation (CSL-JSON Snippet) | Deterministic Resolution Rule & Action |  |
| :---- | :---- | :---- | :---- | :---- |
| **Metadata Source Conflict** | doi \= {10.1101/2024.01.01.12345} (Preprint with a different title on arXiv vs. CrossRef) | {"type": "article-journal", "id": "...", "title": "Official Published Title", "author": \[...\], "DOI": "..."} | **Rule:** CrossRef is the source of truth for published articles.27 | **Action:** Use CrossRef metadata. Log a ConflictWarning noting the discrepancy with the other source. |
| **Author Name Variation** | author \= {Smith, J.H. and Jane Doe} | {"author":} | **Rule:** Normalize all names to a structured format.46 | **Action:** Parse varied inputs into a standard CSL-JSON author array. Standardize initials with spaces (e.g., J. H.). |
| **Title Capitalization** | title \= {{A Study of GPU Computing}} (Forced title case with double braces) | {"title": "A study of GPU computing"} | **Rule:** Store the canonical, unstyled title. Defer casing to the CSL processor.8 | **Action:** Fetch the canonical title from CrossRef. Store it in sentence case in CSL-JSON. The selected .csl file will apply the correct casing on output. |
| **et al. Handling** | author \= {Smith, John and Doe, Jane and Roe, Richard and... \[and 10 others\]} | {"author":} (Full list of 13 authors) | **Rule:** The core tool is agnostic to et al. rules. This is a presentation-layer concern.37 | **Action:** Store the full author list in CSL-JSON. The selected .csl file contains the logic to truncate the list correctly for the final output. |
| **Special Characters** | author \= {García, José} | {"author": \[{"family": "García", "given": "José"}\]} | **Rule:** Store characters as UTF-8 internally. **Action:** Parse unescaped characters. The output generator will apply the correct LaTeX escaping (e.g., Garc{\\'\\i}a) only when generating a .bib file. |  |

---

## **Part 3: Designing the Human-AI Collaboration: The Claude Interaction Model**

The original proposal's integration plan for the AI assistant, Claude, was described as "magical thinking." It lacked a concrete interaction model, leaving critical questions unanswered about how the AI would leverage the new toolset. This section replaces that ambiguity with a technically grounded, robust, and actionable model for AI interaction. It defines a clear role for the AI and specifies the precise mechanisms for communication, task execution, and error handling, drawing on established industry best practices for Large Language Model (LLM) tool use.

### **3.1 Defining the AI's Role: The Programmatic Agent**

There are two primary models for how an AI can interact with a software tool: as a "user" of a Command-Line Interface (CLI) or as a "developer" calling a programmatic API.

The model of an AI acting as a CLI user—effectively "typing" commands and parsing the text output—is a brittle and inefficient metaphor.49 This approach is fraught with problems: it relies on fragile parsing of unstructured text, cannot easily handle the exchange of complex data objects, and makes robust error handling nearly impossible. It is a poor architectural choice for an autonomous agent that needs to perform multi-step reasoning and react to dynamic conditions.51

The correct and vastly superior model is to treat the AI as a **Programmatic Agent**. In this paradigm, the AI's primary role is that of a reasoning engine that interacts with the world through a well-defined Application Programming Interface (API).53 The AI does not "run" the tool; instead, it generates a structured, machine-readable request (typically a JSON object) that specifies which tool to use and what arguments to pass. The refactored Python library, therefore, becomes the API that the AI agent calls. This is the standard, robust pattern for LLM tool use, implemented by all major platforms (e.g., OpenAI Function Calling, Anthropic Tool Use) and frameworks (e.g., LangChain).56

This programmatic agent model offers significant advantages:

* **Structured Data Exchange:** The AI and the tool communicate using structured JSON, not ambiguous natural language. This ensures all data exchanges are precise, reliable, and machine-parseable.55
* **Complex State Management:** The application that orchestrates the AI (the "agent runner") can maintain state between tool calls. This enables complex, multi-step workflows, such as "Find all papers by this author, then check which ones are missing a PDF link, then try to find those PDFs," which would be impossible with a simple CLI.57
* **Robust Error Handling:** The API can be designed to return structured error objects (e.g., a DOIValidationError Python class, serialized to JSON). The AI can then parse this error, understand its meaning, and dynamically decide on a corrective next step, such as retrying with a different search strategy.52

### **3.2 The API is the Conversation**

A surface-level view of tool use is that the AI simply "calls a function." However, a deeper examination of how modern tool-use frameworks operate reveals a more nuanced interaction: a conversational loop.56 This loop proceeds as follows:

1. The user provides a prompt.
2. The AI reasons about the prompt and decides a tool is needed.
3. The AI generates a tool\_call request.
4. The system executes the specified tool with the provided arguments.
5. The system sends a tool\_result back to the AI.
6. The AI receives the result, reasons about it, and generates a final, human-readable response.

This loop is a form of conversation, but the language is not English; the language is the **JSON schema of the API**. The tool\_call is the AI's turn to speak, and the tool\_result is the system's reply.

This reframes the task of designing the Python library's API as an exercise in designing a "language" for the AI agent. The function names, their descriptions, and their parameter schemas constitute the "vocabulary" and "grammar" that the AI will use to reason and act.54 Therefore, the API must be designed with the AI as the primary consumer:

* **Function Names:** Must be clear, descriptive, and action-oriented (e.g., validate\_and\_enrich\_bibliography, search\_by\_title\_author).
* **Function Descriptions:** The docstrings for these functions are not for human developers; they are critical instructions for the AI. They must clearly explain what the tool does, what inputs it expects, and what it returns. This description is what the model uses to decide which tool to select.58
* **Structured Errors:** Errors are not exceptions to be hidden; they are a vital part of the dialogue. A ConflictWarning is not a failure state; it is a piece of information the AI needs to continue the conversation, perhaps by asking the user for clarification ("I found two different author lists for this paper. Which one is correct?").

### **3.3 A Concrete Interaction Example: The "Job to be Done" Workflow**

The following example illustrates the full, end-to-end interaction loop for the primary JTBD defined in Part 1\. This demonstrates how the abstract model translates into a concrete, implementable workflow.

* **Step 1: User Prompt (to the AI Agent)**
  * The user provides a high-level request and the raw data to the agent.
  * **User:** "Please fix this bibliography for my paper. It needs to be in APA 7 style. Here is the BibTeX file: \[...contents of messy.bib...\]"
* **Step 2: AI Generates a Tool Call**
  * The AI, guided by its system prompt and the definitions of the tools it has been given, reasons that the validate\_and\_enrich\_bibliography function is the most appropriate tool for this task. It then generates a JSON object representing the function call, which is passed back to the application.
  * **Generated tool\_call JSON:**
    JSON
    {
      "type": "tool\_use",
      "id": "toolu\_01A09q90qw90lq917835lq9",
      "name": "validate\_and\_enrich\_bibliography",
      "input": {
        "bibtex\_string": "\[...contents of messy.bib...\]",
        "target\_style": "apa.csl"
      }
    }

* **Step 3: System Executes the Tool (Our Python Library)**
  * The agent runner application receives this JSON, parses it, and invokes the corresponding Python function from the refactored library.
  * **Python Call:** result \= library.validate\_and\_enrich\_bibliography(bibtex\_string=..., target\_style=...)
  * The library then executes its core logic: parsing the input BibTeX into internal CSL-JSON objects, querying CrossRef to enrich data, applying the conflict resolution policies defined in Part 2, and using a CSL processor to generate the final, styled bibliography string.
* **Step 4: System Returns a Tool Result**
  * The Python function returns a structured data object containing the results of the operation. The agent runner formats this object into a tool\_result JSON block to send back to the AI for the next turn in the conversation.
  * **Returned tool\_result JSON:**
    JSON
    {
      "type": "tool\_result",
      "tool\_use\_id": "toolu\_01A09q90qw90lq917835lq9",
      "content":,
            "unfixable\_errors":
          }
        }
      \]
    }

* **Step 5: AI Generates the Final Response**
  * The AI receives the structured tool\_result, including the status, summaries, and final output. It synthesizes this information into a helpful, human-readable summary for the end-user.
  * **Final AI Response to User:** "I have successfully validated and reformatted your bibliography in APA 7th edition style. Here is a summary of the changes:
    * I fixed 12 entries that were missing DOIs and normalized 32 author names for consistency.
    * **Warning:** For one paper, I found a conflict between the data you provided and the publisher's official record; I used the publisher's version as the source of truth.
    * Action Required: I could not find a match for the entry keyed 'unknown2024'. Could you please provide a DOI or a more complete title for it?
      Here is the corrected bibliography:
      \[...final bibliography string...\]"

### **3.4 Handling Critical Errors: The AI Feedback Loop**

A key advantage of the programmatic agent model is its ability to gracefully handle errors and attempt self-correction. Consider the scenario where a user provides a BibTeX entry with a syntactically valid but non-existent DOI.

1. **Initial Call:** The AI agent calls the validate\_and\_enrich\_bibliography tool as before.
2. **Tool Execution Failure:** The library's code attempts to query the CrossRef API with the invalid DOI. The API returns a 404 Not Found error.
3. **Structured Error Return:** Instead of crashing, the library's API wrapper is designed to catch this specific exception. It then returns a structured error object as part of the tool\_result.
   JSON
   {
     "type": "tool\_result",
     "tool\_use\_id": "toolu\_01B18r81...",
     "content":
   }

4. **AI's Corrective Action:** The AI agent receives this structured error. Its internal reasoning process, guided by its system prompt, would be: "The DOIValidationError indicates that the primary lookup method failed. My next best strategy is to use a fallback method. I should now try calling the search\_by\_title\_author tool with the title and author information from the original 'smith2023' entry."
5. **New Tool Call:** The AI then generates a *new* tool\_call request for the fallback tool, demonstrating a robust, multi-step, self-correcting workflow. This ability to reason about errors and dynamically choose the next action is the essence of a truly useful and autonomous agent.51

---

## **Part 4: A De-Risked Roadmap: Incremental Value and User-Centric Metrics**

The original five-week plan was criticized as a "deceptively linear" waterfall model. Such an approach, where value is only delivered at the very end, is inherently high-risk. It defers integration, testing, and user feedback, often leading to a "grand reveal" of a product that doesn't meet real-world needs.66 This section replaces that flawed model with a modern, agile roadmap that prioritizes delivering tangible user value early and often. This strategy is guided by a balanced scorecard of metrics that measure true user success, not just developer activity.

### **4.1 The Agile Refactoring Philosophy: Small, Safe, Value-Driven Steps**

The fundamental flaw of the original roadmap is its monolithic nature. A large-scale, multi-week refactoring effort that produces no usable output until completion is a recipe for failure. It creates a long, blind tunnel where developers work on assumptions that may be proven false only at the final, costly integration stage.

The revised approach is rooted in the principles of **incremental refactoring**.68 The project will be broken down into a series of small, manageable sprints. Each sprint will focus on implementing a single, high-value "vertical slice" of functionality. This slice will solve a specific user problem, be built upon the new architecture, be thoroughly tested, and be delivered as a usable feature.69 This methodology aligns with established agile best practices such as the Test-Driven Development (TDD) cycle of "Red-Green-Refactor" and the "Boy Scout Rule" of continuously leaving the codebase cleaner than you found it.66 By refactoring in small, verifiable steps, the team minimizes risk, gets faster feedback, and delivers a steady stream of value to end-users.

### **4.2 Proposed "Phase 1" (2 Weeks): The Author & Title Fixer**

The first sprint must be carefully chosen to deliver the maximum user value while simultaneously de-risking the most critical technical challenges.

* **Justification:** The "Author & Title Fixer" is the ideal candidate for the first incremental release for several reasons:
  * **Addresses the \#1 Pain Point:** As established in Part 1, analysis of common BibTeX errors and the struggles of researchers like Grad-student Greg shows that incorrect author names and inconsistent titles are among the most frequent and frustrating problems they face.8
  * **High Value for Both Personas:** This feature provides immediate, tangible value to both target users. Greg gets his most common errors fixed automatically, increasing his confidence. Paula gets a powerful utility for standardizing author lists from multiple collaborators, saving her significant time.
  * **Technical De-risking:** This "slice" is not a trivial feature. It forces the team to build and validate the most complex and foundational parts of the new architecture at the very beginning of the project. This includes the BibTeX-to-CSL-JSON parser, the CrossRef API client and caching layer, the conflict resolution logic for author and title data, and the final output generator. Successfully delivering this slice proves the viability of the core architectural concepts.
* **Scope of Work for Phase 1:**
  * **Core Logic:** Refactor and/or create the Python modules required for parsing BibTeX into the internal CSL-JSON data model.
  * **Integration:** Implement the CrossRef REST API client, including a robust caching layer to manage API calls efficiently.
  * **Policy Implementation:** Implement the "Metadata Source Hierarchy" and "Author Name Normalization" policies defined in Part 2\.
  * **Deliverable:** Create a single, new, fully functional script (/scripts/workflows/fix\_my\_authors.py) that uses the new library code to take a .bib file as input and produce a corrected version as output.
  * **Testing:** Curate a "Golden Test Set" of 10-15 real-world, problematic .bib files sourced from actual users. This test set will be used to drive development via TDD and will serve as the primary quality gate for the release.67

### **4.3 Defining and Measuring Success: User-Centric vs. Code-Centric Metrics**

A project's metrics define what it values. The original plan's metrics (e.g., lines of code per module, test coverage percentage) measure developer *activity* and code hygiene. While important, they are insufficient because they say nothing about whether the software is actually useful or effective.73 A module can be 100 lines long with 100% test coverage and still be completely useless to the end-user.

To correct this, a balanced scorecard of metrics is required, blending traditional engineering health metrics with user-centric metrics that measure the actual user experience.73 This approach draws from established frameworks in UX research (measuring effectiveness, efficiency, and satisfaction) and DevOps (measuring delivery performance via DORA metrics).76 This provides a holistic view of project success, ensuring the team is accountable for delivering valuable outcomes, not just technical output.

### **Table 3: Phase 1 Success Metrics**

The following table defines the specific, quantifiable success criteria for the two-week "Phase 1" sprint. This provides a clear and unambiguous definition of "done" that is aligned with user and business value.

| Category | Metric | Definition | Target for Phase 1 |
| :---- | :---- | :---- | :---- |
| **User-Centric (Effectiveness)** | **Task Success Rate (TSR)** 76 | The percentage of test participants (representing our personas) who can successfully execute the fix\_my\_authors.py script on a sample messy .bib file without encountering a critical failure or giving up. | \> 95% |
| **User-Centric (Efficiency)** | **Time-to-Value (TTV)** 80 | The median time measured from a new user downloading the script to the moment they successfully generate their first corrected bibliography file. This is the "Aha\!" moment. | \< 5 minutes |
| **User-Centric (Satisfaction)** | **Confidence Score** 19 | The average rating on a 1-5 Likert scale from a post-task survey question: "How confident are you that the author and title information in your bibliography is now correct and properly formatted?" | \> 4.0 / 5.0 |
| **Quality & Reliability** | **Reduction in Manual Work** 82 | The percentage reduction in identifiable, high-priority author and title errors within the "Golden Test Set" after being processed by the script, as verified by manual audit. | \> 80% |
| **Quality & Reliability** | **Golden Test Set Pass Rate** 84 | The percentage of entries in the "Golden Test Set" that are processed by the script without generating unhandled exceptions or producing verifiably incorrect transformations. | \> 95% |
| **Engineering Velocity** | **Cycle Time** (DORA Metric) 75 | The median time from the first commit on a feature branch related to this phase to its merge into the main branch, representing a deployable state. | \< 1 week |

---

## **Conclusion: A Plan for Building the Right System**

This addendum has systematically de-risked the "Deep-Biblio-Tools" refactoring project by addressing the critical strategic weaknesses identified in the initial proposal. By moving beyond a purely technical perspective, it has laid a new foundation for success.

The project is now grounded in the reality of its users, with validated personas whose frustrations and goals will guide every decision. The "chaotic hellscape" of bibliographic data will be tamed not by ad-hoc fixes, but by a robust architectural decision to use a neutral internal data model and a set of deterministic policies for handling conflict. The "magical thinking" around AI has been replaced with a concrete, industry-standard programmatic agent model that defines a clear and powerful role for the AI assistant, Claude. Finally, the high-risk waterfall roadmap has been supplanted by an agile, incremental plan that prioritizes delivering tangible value early and measures success through the lens of the user.

By adopting the strategies outlined in this document, the project is transformed. It is no longer a purely technical exercise in code improvement. It is a strategic initiative focused on building a product that is demonstrably useful, reliable, and valued by the academic community it aims to serve. We are no longer just building a beautiful engine; we are building a vehicle with a driver, a map, and a clear destination.

#### **Works cited**

1. How to Define a User Persona \[2025 Complete Guide\] \- CareerFoundry, accessed August 4, 2025, [https://careerfoundry.com/en/blog/ux-design/how-to-define-a-user-persona/](https://careerfoundry.com/en/blog/ux-design/how-to-define-a-user-persona/)
2. Application of Personas in User Interface Design for Educational Software \- ResearchGate, accessed August 4, 2025, [https://www.researchgate.net/publication/220832217\_Application\_of\_Personas\_in\_User\_Interface\_Design\_for\_Educational\_Software](https://www.researchgate.net/publication/220832217_Application_of_Personas_in_User_Interface_Design_for_Educational_Software)
3. User Personas | NC State University Libraries, accessed August 4, 2025, [https://www.lib.ncsu.edu/projects/user-personas](https://www.lib.ncsu.edu/projects/user-personas)
4. User Personas \- OERTX, accessed August 4, 2025, [https://oertx.highered.texas.gov/courseware/lesson/4914/overview](https://oertx.highered.texas.gov/courseware/lesson/4914/overview)
5. (PDF) Graduate Student Use and Non-use of Reference and PDF Management Software: An Exploratory Study \- ResearchGate, accessed August 4, 2025, [https://www.researchgate.net/publication/328351395\_Graduate\_Student\_Use\_and\_Non-use\_of\_Reference\_and\_PDF\_Management\_Software\_An\_Exploratory\_Study](https://www.researchgate.net/publication/328351395_Graduate_Student_Use_and_Non-use_of_Reference_and_PDF_Management_Software_An_Exploratory_Study)
6. Library of user personas for open data \- Roadmap to Informed Communities, accessed August 4, 2025, [https://communities.sunlightfoundation.com/discovery/personas-library/](https://communities.sunlightfoundation.com/discovery/personas-library/)
7. The Biggest Mistakes You Should Never Make in the Postdoc And How to Avoid or Recover From Them \- YouTube, accessed August 4, 2025, [https://www.youtube.com/watch?v=z5LM-g2Pvh8](https://www.youtube.com/watch?v=z5LM-g2Pvh8)
8. How to not mess up your bibliographies with Bibtex \- Claus O. Wilke, accessed August 4, 2025, [https://clauswilke.com/blog/2015/10/02/bibtex/](https://clauswilke.com/blog/2015/10/02/bibtex/)
9. 5 Common Mistakes When Using Citation Tools and How to Fix Them \- PaperGen, accessed August 4, 2025, [https://www.papergen.ai/blog/5-common-mistakes](https://www.papergen.ai/blog/5-common-mistakes)
10. PERSPECTIVES OF EFL DOCTORAL STUDENTS ON CHALLENGES OF CITATIONS IN ACADEMIC WRITING \- ERIC, accessed August 4, 2025, [https://files.eric.ed.gov/fulltext/EJ1166743.pdf](https://files.eric.ed.gov/fulltext/EJ1166743.pdf)
11. Whats the difference between a APA, MLA and Chicago Style Essay/Research Paper and what majors use each? \- Reddit, accessed August 4, 2025, [https://www.reddit.com/r/college/comments/5j4xrg/whats\_the\_difference\_between\_a\_apa\_mla\_and/](https://www.reddit.com/r/college/comments/5j4xrg/whats_the_difference_between_a_apa_mla_and/)
12. MLA vs. APA vs. Chicago – Which do I use? \- NoodleTools Help Desk, accessed August 4, 2025, [https://noodletools.freshdesk.com/support/solutions/articles/6000119177-mla-vs-apa-vs-chicago-which-do-i-use-](https://noodletools.freshdesk.com/support/solutions/articles/6000119177-mla-vs-apa-vs-chicago-which-do-i-use-)
13. 10 Common Citation Errors in Academic Writing \- Yomu AI, accessed August 4, 2025, [https://www.yomu.ai/blog/10-common-citation-errors-in-academic-writing](https://www.yomu.ai/blog/10-common-citation-errors-in-academic-writing)
14. Citation Frustration? These Sources Will Help. \- Bentley University, accessed August 4, 2025, [https://www.bentley.edu/library/in-the-know/citation-frustration-these-sources-will-help](https://www.bentley.edu/library/in-the-know/citation-frustration-these-sources-will-help)
15. Common Referencing Errors Committed by Graduate Students in Education, accessed August 4, 2025, [https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=7496\&context=libphilprac](https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=7496&context=libphilprac)
16. Using Citation Generators Responsibly \- Purdue OWL, accessed August 4, 2025, [https://owl.purdue.edu/owl/research\_and\_citation/using\_citation\_machines\_responsibly.html](https://owl.purdue.edu/owl/research_and_citation/using_citation_machines_responsibly.html)
17. Taking care of references – the nightmare of every researcher \- eCORRECTOR, accessed August 4, 2025, [https://ecorrector.com/taking-care-of-references-the-nightmare-of-every-researcher/](https://ecorrector.com/taking-care-of-references-the-nightmare-of-every-researcher/)
18. Citation Management – Navigating the Research Lifecycle for the Modern Researcher, accessed August 4, 2025, [https://colorado.pressbooks.pub/researchlifecycle/chapter/citation-management-2/](https://colorado.pressbooks.pub/researchlifecycle/chapter/citation-management-2/)
19. Survey techniques for measuring confidence using 4+ Scores | by Reuben Ray \- Medium, accessed August 4, 2025, [https://reubenray.medium.com/survey-techniques-for-measuring-confidence-using-4-scores-7b3891c5c6a4](https://reubenray.medium.com/survey-techniques-for-measuring-confidence-using-4-scores-7b3891c5c6a4)
20. Easily create and manage your references and citations \- RefWorks \- ProQuest, accessed August 4, 2025, [https://refworks.proquest.com/learn-more/](https://refworks.proquest.com/learn-more/)
21. Create a research workflow \- Knowledge Base \- vLex, accessed August 4, 2025, [https://support.vlex.com/support-1/frequently-asked-questions/research-using-folders](https://support.vlex.com/support-1/frequently-asked-questions/research-using-folders)
22. The Benefits of User Personas for Your edTech Product \- Backpack Interactive, accessed August 4, 2025, [https://backpackinteractive.com/insights/benefits-of-user-personas-edtech-product/](https://backpackinteractive.com/insights/benefits-of-user-personas-edtech-product/)
23. Fix BibTeX Errors: Free Online Validator for LaTeX Bibliography Issues | 2025 \- lode.de, accessed August 4, 2025, [https://www.lode.de/blog/fix-your-bibtex-errors-instantly-a-comprehensive-guide-to-common-latex-bibliography-issues](https://www.lode.de/blog/fix-your-bibtex-errors-instantly-a-comprehensive-guide-to-common-latex-bibliography-issues)
24. \[2503.11853\] Evaluating Multilingual Metadata Quality in Crossref \- arXiv, accessed August 4, 2025, [https://arxiv.org/abs/2503.11853](https://arxiv.org/abs/2503.11853)
25. Analysis of the Publication and Document Types in OpenAlex, Web of Science, Scopus, Pubmed and Semantic Scholar \- arXiv, accessed August 4, 2025, [https://arxiv.org/html/2406.15154v1](https://arxiv.org/html/2406.15154v1)
26. Large-scale comparison of bibliographic data sources: Scopus, Web of Science, Dimensions, Crossref, and Microsoft Academic \- MIT Press Direct, accessed August 4, 2025, [https://direct.mit.edu/qss/article/2/1/20/97574/Large-scale-comparison-of-bibliographic-data](https://direct.mit.edu/qss/article/2/1/20/97574/Large-scale-comparison-of-bibliographic-data)
27. REST API \- Crossref, accessed August 4, 2025, [https://www.crossref.org/documentation/retrieve-metadata/rest-api/](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
28. Documentation \- Metadata Retrieval \- Crossref, accessed August 4, 2025, [https://www.crossref.org/documentation/retrieve-metadata/](https://www.crossref.org/documentation/retrieve-metadata/)
29. Introduction to posted content (includes preprints) \- Crossref, accessed August 4, 2025, [https://www.crossref.org/documentation/research-nexus/posted-content-includes-preprints/](https://www.crossref.org/documentation/research-nexus/posted-content-includes-preprints/)
30. Crossref metadata for preprints: Discussions and recommendations \- OSF, accessed August 4, 2025, [https://osf.io/preprints/metaarxiv/qzusj/download](https://osf.io/preprints/metaarxiv/qzusj/download)
31. Crossref Preprint AG recommendations \- 2022, accessed August 4, 2025, [https://www.crossref.org/pdfs/preprint-ag-recommendations-2022-07.pdf](https://www.crossref.org/pdfs/preprint-ag-recommendations-2022-07.pdf)
32. Blog \- Using the Crossref REST API. Part 9 (with Dimensions), accessed August 4, 2025, [https://www.crossref.org/blog/using-the-crossref-rest-api.-part-9-with-dimensions/](https://www.crossref.org/blog/using-the-crossref-rest-api.-part-9-with-dimensions/)
33. Common Errors in Bibliographies John Owens, accessed August 4, 2025, [https://www.ece.ucdavis.edu/\~jowens/biberrors.html](https://www.ece.ucdavis.edu/~jowens/biberrors.html)
34. Reference Management Software \- Research Solutions, accessed August 4, 2025, [https://www.researchsolutions.com/products/reference-management](https://www.researchsolutions.com/products/reference-management)
35. Bibtex bibliography styles \- Overleaf, Online LaTeX Editor, accessed August 4, 2025, [https://www.overleaf.com/learn/latex/Bibtex\_bibliography\_styles](https://www.overleaf.com/learn/latex/Bibtex_bibliography_styles)
36. Mastering Bibliography Styles in LaTeX/Overleaf: A Quick Guide for BibTeX, natbib, and BibLaTeX | CiteDrive, accessed August 4, 2025, [https://www.citedrive.com/en/blog/mastering-bibliography-styles-latex-guide-bibtex-natbib-biblatex/](https://www.citedrive.com/en/blog/mastering-bibliography-styles-latex-guide-bibtex-natbib-biblatex/)
37. Et Al. | Meaning & Use in APA, MLA & Chicago \- Scribbr, accessed August 4, 2025, [https://www.scribbr.com/citing-sources/et-al/](https://www.scribbr.com/citing-sources/et-al/)
38. How to Effectively Use "Et al." in APA, MLA, and Chicago Style \- Enago, accessed August 4, 2025, [https://www.enago.com/thesis-editing/blog/how-to-effectively-use-et-al-in-apa-mla-and-chicago-style](https://www.enago.com/thesis-editing/blog/how-to-effectively-use-et-al-in-apa-mla-and-chicago-style)
39. The Proper Use of Et Al. in APA Style, accessed August 4, 2025, [https://blog.apastyle.org/apastyle/2011/11/the-proper-use-of-et-al-in-apa-style.html](https://blog.apastyle.org/apastyle/2011/11/the-proper-use-of-et-al-in-apa-style.html)
40. Citation Style Language, accessed August 4, 2025, [https://citationstyles.org/](https://citationstyles.org/)
41. Zotero Style Repository, accessed August 4, 2025, [https://www.zotero.org/styles](https://www.zotero.org/styles)
42. csl-citation.txt \- Mendeley CSL, accessed August 4, 2025, [https://csl.mendeley.com/cslEditorLib/external/csl-schema/csl-citation.txt](https://csl.mendeley.com/cslEditorLib/external/csl-schema/csl-citation.txt)
43. CSL-JSON Schema \- FAIRsharing.org, accessed August 4, 2025, [https://fairsharing.org/1385](https://fairsharing.org/1385)
44. Citation Style Language \- Wikipedia, accessed August 4, 2025, [https://en.wikipedia.org/wiki/Citation\_Style\_Language](https://en.wikipedia.org/wiki/Citation_Style_Language)
45. Running the Processor — citeproc-js 1.1.73 documentation \- Read the Docs, accessed August 4, 2025, [https://citeproc-js.readthedocs.io/en/latest/running.html](https://citeproc-js.readthedocs.io/en/latest/running.html)
46. Citation Style Language \- Code4Lib wiki, accessed August 4, 2025, [https://wiki.code4lib.org/Citation\_Style\_Language](https://wiki.code4lib.org/Citation_Style_Language)
47. Substack & Science \- Technical Support \- Crossref community forum, accessed August 4, 2025, [https://community.crossref.org/t/substack-science/4179](https://community.crossref.org/t/substack-science/4179)
48. Official repository for Citation Style Language (CSL) citation styles. \- GitHub, accessed August 4, 2025, [https://github.com/citation-style-language/styles](https://github.com/citation-style-language/styles)
49. API vs CLI \- DEV Community, accessed August 4, 2025, [https://dev.to/serverspace/api-vs-cli-21k5](https://dev.to/serverspace/api-vs-cli-21k5)
50. What's The Difference Between CLIs and APIs?, accessed August 4, 2025, [https://nordicapis.com/whats-the-difference-between-clis-and-apis/](https://nordicapis.com/whats-the-difference-between-clis-and-apis/)
51. What is the difference between an AI agent and a background job calling LLM API? \- Reddit, accessed August 4, 2025, [https://www.reddit.com/r/LocalLLaMA/comments/1jdawqj/what\_is\_the\_difference\_between\_an\_ai\_agent\_and\_a/](https://www.reddit.com/r/LocalLLaMA/comments/1jdawqj/what_is_the_difference_between_an_ai_agent_and_a/)
52. MCP vs APIs: When to Use Which for AI Agent Development \- Tinybird, accessed August 4, 2025, [https://www.tinybird.co/blog-posts/mcp-vs-apis-when-to-use-which-for-ai-agent-development](https://www.tinybird.co/blog-posts/mcp-vs-apis-when-to-use-which-for-ai-agent-development)
53. Difference between API and CLI \- Stack Overflow, accessed August 4, 2025, [https://stackoverflow.com/questions/63191743/difference-between-api-and-cli](https://stackoverflow.com/questions/63191743/difference-between-api-and-cli)
54. arxiv.org, accessed August 4, 2025, [https://arxiv.org/html/2507.08034v1\#:\~:text=These%20schemas%20act%20like%20blueprints,the%20LLM's%20internal%20processing%20capabilities.](https://arxiv.org/html/2507.08034v1#:~:text=These%20schemas%20act%20like%20blueprints,the%20LLM's%20internal%20processing%20capabilities.)
55. LLMs \+ Tools \= | How to Extend AI Capabilities with External Integrations \- Medium, accessed August 4, 2025, [https://medium.com/@hy287719/llms-tools-how-to-extend-ai-capabilities-with-external-integrations-96694ff9a9f6](https://medium.com/@hy287719/llms-tools-how-to-extend-ai-capabilities-with-external-integrations-96694ff9a9f6)
56. Integrating Large Language Models with External Tools: A Practical Guide to API Function Calls \- Complere Infosystem, accessed August 4, 2025, [https://complereinfosystem.com/integrate-large-language-models-with-external-tools](https://complereinfosystem.com/integrate-large-language-models-with-external-tools)
57. Tool use with Claude \- Anthropic API, accessed August 4, 2025, [https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview)
58. Tool calling | 🦜️ LangChain, accessed August 4, 2025, [https://python.langchain.com/docs/concepts/tool\_calling/](https://python.langchain.com/docs/concepts/tool_calling/)
59. How to use function calling with Azure OpenAI in Azure AI Foundry Models \- Microsoft Learn, accessed August 4, 2025, [https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/function-calling](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/function-calling)
60. Assistants Function Calling \- OpenAI API, accessed August 4, 2025, [https://platform.openai.com/docs/assistants/tools/function-calling](https://platform.openai.com/docs/assistants/tools/function-calling)
61. Integrating External Tools with Large Language Models (LLM) to Improve Accuracy \- arXiv, accessed August 4, 2025, [https://arxiv.org/html/2507.08034v1](https://arxiv.org/html/2507.08034v1)
62. Guide to Tool Calling in LLMs \- Analytics Vidhya, accessed August 4, 2025, [https://www.analyticsvidhya.com/blog/2024/08/tool-calling-in-llms/](https://www.analyticsvidhya.com/blog/2024/08/tool-calling-in-llms/)
63. Large language model \- Wikipedia, accessed August 4, 2025, [https://en.wikipedia.org/wiki/Large\_language\_model](https://en.wikipedia.org/wiki/Large_language_model)
64. tools — LangChain documentation, accessed August 4, 2025, [https://python.langchain.com/api\_reference/community/tools.html](https://python.langchain.com/api_reference/community/tools.html)
65. How to create tools | 🦜️ LangChain, accessed August 4, 2025, [https://python.langchain.com/docs/how\_to/custom\_tools/](https://python.langchain.com/docs/how_to/custom_tools/)
66. Agile Refactoring: Techniques, Best Practices & Challenges \- Brainhub, accessed August 4, 2025, [https://brainhub.eu/library/refactoring-in-agile-techniques-best-practices](https://brainhub.eu/library/refactoring-in-agile-techniques-best-practices)
67. Refactoring in Agile: A Guide \- Number Analytics, accessed August 4, 2025, [https://www.numberanalytics.com/blog/ultimate-guide-code-refactoring-agile-development](https://www.numberanalytics.com/blog/ultimate-guide-code-refactoring-agile-development)
68. refraction.dev, accessed August 4, 2025, [https://refraction.dev/blog/refactoring-legacy-code-outdated-software\#:\~:text=Incremental%20refactoring%20involves%20making%20small,functionality%20while%20improving%20its%20quality.](https://refraction.dev/blog/refactoring-legacy-code-outdated-software#:~:text=Incremental%20refactoring%20involves%20making%20small,functionality%20while%20improving%20its%20quality.)
69. Code Refactoring: 6 Techniques and 5 Critical Best Practices \- CodeSee, accessed August 4, 2025, [https://www.codesee.io/learning-center/code-refactoring](https://www.codesee.io/learning-center/code-refactoring)
70. Techniques for Refactoring Legacy Code \- DEV Community, accessed August 4, 2025, [https://dev.to/wallacefreitas/techniques-for-refactoring-legacy-code-1003](https://dev.to/wallacefreitas/techniques-for-refactoring-legacy-code-1003)
71. Code Refactoring in 2025: Best Practices & Popular Techniques \- Maruti Techlabs, accessed August 4, 2025, [https://marutitech.com/code-refactoring-best-practices/](https://marutitech.com/code-refactoring-best-practices/)
72. (PDF) Challenges with Reference Citations among Postgraduate Students at the Kwame Nkrumah University of Science and Technology, Kumasi, Ghana \- ResearchGate, accessed August 4, 2025, [https://www.researchgate.net/publication/236694677\_Challenges\_with\_Reference\_Citations\_among\_Postgraduate\_Students\_at\_the\_Kwame\_Nkrumah\_University\_of\_Science\_and\_Technology\_Kumasi\_Ghana](https://www.researchgate.net/publication/236694677_Challenges_with_Reference_Citations_among_Postgraduate_Students_at_the_Kwame_Nkrumah_University_of_Science_and_Technology_Kumasi_Ghana)
73. How to measure developer productivity | BrowserStack, accessed August 4, 2025, [https://www.browserstack.com/guide/productivity-metrics-in-software-engineering](https://www.browserstack.com/guide/productivity-metrics-in-software-engineering)
74. How to evaluate refactoring decisions? The 4W's framework : r/programming \- Reddit, accessed August 4, 2025, [https://www.reddit.com/r/programming/comments/11wx63i/how\_to\_evaluate\_refactoring\_decisions\_the\_4ws/](https://www.reddit.com/r/programming/comments/11wx63i/how_to_evaluate_refactoring_decisions_the_4ws/)
75. How To Measure Developer Productivity (+Key Metrics) \- Jellyfish.co, accessed August 4, 2025, [https://jellyfish.co/blog/how-to-measure-developer-productivity/](https://jellyfish.co/blog/how-to-measure-developer-productivity/)
76. 6 UX Metrics and KPIs to Measure User Experience in 2025 \- Survicate, accessed August 4, 2025, [https://survicate.com/blog/ux-metrics/](https://survicate.com/blog/ux-metrics/)
77. Understanding User-Centric Metrics in Digital Experience Monitoring (DEM) \- Site24x7 Blog, accessed August 4, 2025, [https://www.site24x7.com/blog/user-centric-metrics-digital-experience-monitoring](https://www.site24x7.com/blog/user-centric-metrics-digital-experience-monitoring)
78. The Role of Usability Metrics in User-Centered Design | Optimal Workshop, accessed August 4, 2025, [https://www.optimalworkshop.com/blog/usability-metrics](https://www.optimalworkshop.com/blog/usability-metrics)
79. The 20 most popular developer productivity metrics: a practical reference for leaders \- Blog, accessed August 4, 2025, [https://www.gitpod.io/blog/20-most-popular-developer-productivity-metrics](https://www.gitpod.io/blog/20-most-popular-developer-productivity-metrics)
80. whatfix.com, accessed August 4, 2025, [https://whatfix.com/blog/time-to-value/\#:\~:text=Define%20the%20%E2%80%9Cend%E2%80%9D%20point%3A,product's%20time%2Dto%2Dvalue.](https://whatfix.com/blog/time-to-value/#:~:text=Define%20the%20%E2%80%9Cend%E2%80%9D%20point%3A,product's%20time%2Dto%2Dvalue.)
81. Time-to-Value: How to Track & Reduce TTV \- Whatfix, accessed August 4, 2025, [https://whatfix.com/blog/time-to-value/](https://whatfix.com/blog/time-to-value/)
82. How to Calculate Test Automation ROI | BrowserStack, accessed August 4, 2025, [https://www.browserstack.com/guide/calculate-test-automation-roi](https://www.browserstack.com/guide/calculate-test-automation-roi)
83. Calculating the Time Wasted on Repetitive Manual Tasks \- TeamDynamix, accessed August 4, 2025, [https://www.teamdynamix.com/blog/calculating-the-time-wasted-on-repetitive-manual-tasks/](https://www.teamdynamix.com/blog/calculating-the-time-wasted-on-repetitive-manual-tasks/)
84. The Power of Code Refactoring: How to Measure Refactoring Success \- Stepsize AI, accessed August 4, 2025, [https://www.stepsize.com/blog/how-to-measure-refactoring-success](https://www.stepsize.com/blog/how-to-measure-refactoring-success)
85. Code Refactoring Risks & Success Metrics: Ensure Smooth Progress \- Forgeahead, accessed August 4, 2025, [https://forgeahead.io/blog/code-refactoring-risks-and-success-metrics](https://forgeahead.io/blog/code-refactoring-risks-and-success-metrics)
