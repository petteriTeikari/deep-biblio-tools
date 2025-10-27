# Physics-Based Virtual Try-On: Bridging Manufacturing CAD and Photorealistic 4D Gaussian Splatting for Fashion

**Status**: Foundation manuscript for standalone paper (2026)
**Target**: ~50kB comprehensive research synthesis
**Version**: v2 - Integrated fashion research community perspectives

**Last Updated**: October 2025

---

## Abstract

Current 4D Gaussian Splatting (4DGS) methods for clothed human avatars achieve photorealistic rendering but fail to address a critical use case: **virtual try-on for validating garment fit on diverse body shapes**. This gap has practical consequences: fashion practitioners require **±5-10mm fit accuracy** to eliminate physical samples [Oh & Kim 2025], yet existing approaches—including D3GA, 3DGS-Avatar, and MPMAvatar—either use learned deformation models that cannot generalize beyond training data or physics-based simulations never evaluated for body shape generalization.

We present a comprehensive analysis bridging **computer vision 4DGS research** and **fashion technology requirements**, demonstrating through systematic literature review that: (1) learned 4DGS methods train person-specific models incompatible with virtual try-on; (2) physics-based MPMAvatar models anisotropic fabric mechanics but lacks virtual try-on evaluation; (3) the manufacturing-rendering loop—where validated CAD patterns inform photorealistic drape simulation—remains an open research challenge; and (4) fashion practitioners require **interpretable simulation** that explains causal relationships between fabric parameters and drape outcomes [Ryu & Lee 2025].

Recent advances in world models for robotics [Ctrl-World, Guo et al. 2025] offer promising architecture patterns: multi-view joint prediction reduces hallucinations in contact-rich interactions (analogous to garment-body contact zones), frame-level conditioning enables mm-level controllability, and pose-conditioned memory prevents error accumulation over long-horizon sequences. However, cloth simulation presents unique challenges—anisotropic mechanics, large deformations, material diversity—requiring domain-specific extensions.

Our synthesis identifies five critical research directions for closing the virtual try-on validation gap, emphasizing that **physics-based fabric modeling is essential** because virtual try-on cannot "cheat" by modifying body shapes to fit garments—simulation must accurately capture how specific fabrics drape on specific individuals. We propose an architecture integrating Material Point Method simulation with neurosymbolic CAD, enabling bidirectional workflows where patterns validate against realistic drape and drape simulations inform pattern adjustments.

This work positions virtual try-on not merely as marketing technology but as **manufacturing validation tool** with quantifiable sustainability impact: eliminating 60-80% of physical fit samples saves ~700,000 liters of water per season for a medium-size fashion brand [MDPI Sustainability 2025]. Success requires collaboration between computer vision researchers (efficient physics simulation, photorealistic rendering) and fashion practitioners (manufacturing validity, designer workflows, sustainability metrics).

**Keywords**: 4D Gaussian Splatting, virtual try-on, physics-based simulation, Material Point Method, fashion CAD, fabric mechanics, anisotropic drape, body shape generalization, world models, sustainability

---

## 1. Introduction

### 1.1 The Virtual Try-On Problem: Fashion Industry Perspective

Virtual try-on technology promises to revolutionize not just e-commerce visualization but **manufacturing validation**, enabling designers to eliminate physical samples while ensuring fit accuracy [MDPI Sustainability 2025]. However, as recent fashion research demonstrates, success requires more than photorealistic rendering—it demands **manufacturing-level accuracy** that fashion practitioners can trust for production decisions.

Recent work on generative AI for fashion design [Ryu & Lee 2025] revealed that even 2D image generation requires "expertly worded prompts" to achieve 67.6% accuracy, highlighting that **fashion expertise remains central** even with powerful AI tools. This raises a critical question for 3D drape simulation: if generating a 2D fashion illustration requires expert guidance, what level of physics-based modeling is necessary for 3D virtual try-on to achieve manufacturing-grade accuracy?

The fashion industry defines virtual try-on success not by rendering quality metrics (PSNR, SSIM) but by **practical decision-enabling criteria**:

- **Pre-production testing**: Does this pattern fit the size range correctly before cutting fabric?
- **Fit tolerance**: ±5-10mm accuracy threshold (industry practitioners' requirement for eliminating physical samples) [Oh & Kim 2025]
- **Customization verification**: Does the tailored pattern actually fit this customer's measurements?
- **Sustainability impact**: Can we quantify sample elimination and waste reduction?

This constraint becomes critical when virtual try-on serves not just marketing but **manufacturing validation**. Unlike marketing visualizations that can "adapt" garments to look appealing, accurate virtual try-on must respect physical constraints—you cannot modify a person's actual body shape to make clothing fit better.

### 1.2 The Manufacturing CAD Connection

Recent advances in neurosymbolic fashion CAD—exemplified by GarmentCode [Xiang et al., 2024] and Design2GarmentCode [Zhou et al., 2024]—have demonstrated the ability to generate **manufacturing-ready patterns** that satisfy geometric constraints like seam matching (±3% tolerance) and grain alignment (±2°). However, these systems validate **geometric validity** (can the pattern be sewn?) but not **mechanical validity** (does it drape realistically on this body?).

A pattern can pass all geometric constraints yet still fit poorly if fabric mechanics aren't modeled during drape prediction. This gap motivates our core research question:

**Research Question**: Given a manufacturing-ready pattern and a novel individual's body scan, can physics-based 4D Gaussian Splatting accurately simulate drape that matches how the physical garment would actually fit?

### 1.3 Current State of 4DGS for Garments

Our systematic review of 4DGS literature reveals three categories of approaches:

**Learned Deformation Models** (D3GA, 3DGS-Avatar):
- Train person-specific neural networks mapping poses to garment deformations
- Achieve photorealistic rendering with fast inference (50+ FPS)
- **Cannot generalize to unseen body shapes** - fatal flaw for virtual try-on
- As Sun et al.'s [2025] review notes, **data-driven methods fundamentally learn correlations in training data rather than modeling the physical laws governing fabric behavior**

**Physics-Based Simulation** (MPMAvatar):
- Material Point Method models anisotropic fabric properties (stiffness, shear, bending)
- "Zero-shot generalizable to interactions with an unseen external object" [Lee et al., 2025]
- **Should generalize to new body shapes** due to physics foundation
- **Never evaluated for virtual try-on** - no validation on body shape diversity
- Too slow for interactivity (1.1 seconds/frame vs <5 second requirement [Digital Creativity 2025])

**Reconstruction Methods** (Gaussian Garments, ClothingTwin):
- Focus on capturing existing garments from multi-view video
- **Output 3D meshes, not 2D patterns** - no manufacturing CAD integration
- Neglect fabric thickness and manufacturing constraints

**Critical Gap**: NO existing work validates manufacturing CAD patterns → 4DGS drape → comparison with physical reality across body shape variations.

### 1.4 World Models for Predictive Simulation

Recent advances in world models for robotics offer compelling insights for fashion virtual try-on. Ctrl-World [Guo et al., 2025] demonstrated that world models enabling "policy-in-the-loop rollouts" can validate robotic manipulation behaviors through simulation before physical deployment—directly analogous to validating garment fit through virtual try-on before fabric cutting.

**Key Technical Innovations with Fashion Parallels**:

1. **Multi-View Joint Prediction**: Ctrl-World jointly predicts across multiple camera views to "substantially reduce hallucinations" during **contact-rich interactions**. For fashion virtual try-on, garment-body contact zones (shoulder seams, waistbands, armholes) represent analogous contact-rich regions where simulation accuracy is critical.

2. **Frame-Level Action Conditioning**: Achieves "centimeter-level controllability" through pose-conditioned per-frame synthesis. Fashion manufacturing demands **millimeter-level precision**—seam allowances of 1.5cm, dart placement within ±2mm.

3. **Pose-Conditioned Memory Retrieval**: Prevents "prediction errors in world models" from accumulating over long-horizon rollouts (20+ seconds). Garment drape simulation faces analogous temporal consistency challenges across pose sequences.

**The Manufacturing Validation Parallel**: Ctrl-World enabled "targeted policy improvement through synthetic trajectories" with 44.7% success rate gains. Fashion virtual try-on seeks identical capability: **validate pattern fit through simulation before physical sampling**.

However, cloth presents unique challenges: anisotropic mechanics, large deformations, material diversity, and body shape variability beyond rigid object manipulation.

### 1.5 Contribution and Structure

This paper makes four contributions:

1. **Systematic Literature Review**: Comprehensive analysis of 6 core 4DGS papers with verified limitation quotes, identifying the virtual try-on validation gap

2. **Fashion-CS Research Bridge**: Integration of fashion practitioner requirements (±mm accuracy, <5 sec iteration, interpretability) with computer vision capabilities

3. **World Model Architecture Adaptation**: Extension of robotics world model patterns (multi-view prediction, fine-grained conditioning, temporal memory) to cloth simulation

4. **Research Roadmap**: Five critical research directions with technical specifications for closing the gap between manufacturing CAD and virtual try-on validation, including sustainability impact quantification

The remainder of this paper is structured as follows: Section 2 reviews related work in 4DGS reconstruction, physics-based cloth simulation, world models, and fashion technology requirements. Section 3 presents our systematic analysis of current 4DGS approaches with verified limitations. Section 4 details the virtual try-on validation gap emphasizing body shape generalization and fashion practitioner needs. Section 5 proposes the manufacturing-rendering loop architecture. Section 6 outlines research priorities including four-level validation framework. Section 7 discusses community collaboration and sustainability impact. Section 8 concludes.

---

## 2. Background and Related Work

### 2.1 Evolution of 3D Gaussian Splatting

3D Gaussian Splatting [Kerbl et al., 2023] revolutionized novel view synthesis by representing scenes as collections of 3D Gaussians with learnable parameters (position, covariance, opacity, spherical harmonics for view-dependent color). The method's key advantages—differentiability, fast rasterization, and explicit geometry—enabled real-time rendering with photorealistic quality.

For fashion, the challenge differs from static scene reconstruction: garment surfaces are approximately developable (can be flattened to 2D patterns), but the critical requirement is **modeling dynamic deformation** under physics constraints, not optimizing static primitive geometry.

### 2.2 4D Gaussian Splatting for Dynamic Scenes

Extending 3DGS to temporal dimensions, 4D Gaussian Splatting [Wu et al., 2024] introduced methods for dynamic scene reconstruction through modeling Gaussians' temporal evolution via deformation fields.

For clothed humans, this evolution took two paths:

**Path 1: Learned Deformation**
- Train neural networks mapping skeletal poses to Gaussian transformations
- Efficient inference (real-time rendering)
- **Limited generalization**: trained on specific individuals

**Path 2: Physics-Based Deformation**
- Simulate fabric mechanics using FEM/MPM/Position-Based Dynamics
- Slower but generalizable to novel scenarios
- **Underexplored for garments**: most physics research focuses on animation, not virtual try-on

### 2.3 Garment-Specific 4DGS Methods (Condensed Review)

**Gaussian Garments** [Rong et al., 2024] - 3DV 2025
- Multi-view reconstruction combining 3D meshes with Gaussian textures
- **Limitations**: "assumes scenes with uniform lighting," "details such as collars and pockets are represented using appearance model rather than explicit geometry"

**ClothingTwin** [Wang et al., 2025] - arXiv
- Inner/outer fabric layer reconstruction without mannequin removal
- **Limitation**: "neglect the thickness of garments," outputs meshes not manufacturing patterns

**D3GA** [Zielonka et al., 2023] - ICCV 2023
- Person-specific learned deformation via tracking-based training
- **Limitations**: "requires per-frame garment templates for long and loose garments," no body shape generalization

**3DGS-Avatar** [Qian et al., 2024] - CVPR 2024
- Fast training (30 minutes) for animatable avatars
- **Limitations**: "difficulty with extreme out-of-distribution poses," "struggles with loose-fitting clothing"

**MPMAvatar** [Lee et al., 2025] - SIGGRAPH 2025
- Material Point Method with anisotropic fabric modeling
- **Key Quote**: "zero-shot generalizable to interactions with an unseen external object"
- **Critical Gap**: Never evaluated for body shape diversity or virtual try-on scenarios
- Performance: 1.1 seconds/frame (vs <5 sec requirement for designer workflows)

**OGC (Offset Gaussian Contacts)** [Miao et al., 2025] - arXiv
- Offset surface model for cloth-body contact
- **Gap**: No manufacturing CAD integration, focuses on animation not fit validation

### 2.4 Fashion Technology Requirements

Recent fashion research establishes practical requirements often overlooked by computer vision work:

**Body-Fit Pattern Generation** [Oh & Kim 2025]: "Computational methods demonstrate new ways of rendering body-to-pattern relationships" but validation still requires **physical garment construction**. Their landmark matching algorithm addresses a critical challenge: patterns must adapt to individual anthropometric variations while preserving style lines. The algorithm validates by comparing generated patterns against **commercial pattern company standards** and testing fit on actual garment construction—establishing that physical validation, not just simulation metrics, is the gold standard.

The critical question: can 4DGS drape simulation accurately predict whether a pattern will fit **before cutting fabric**?

**Anthropometric Diversity Challenge**: Fashion practitioners must accommodate:
- **Size range**: Typically 8-12 sizes (XS-3XL) from single pattern
- **Body proportions**: Different torso lengths, shoulder widths, hip-waist ratios
- **Postural variations**: Different shoulder slopes, spinal curvatures, arm positions

Virtual try-on cannot simply scale a single body model—different sizes have different proportional relationships (e.g., larger sizes may have proportionally wider shoulders relative to waist). This non-linear scaling creates complex drape interactions that learned models cannot generalize to without physics-based foundations.

**Parametric Design Workflows** [Digital Creativity 2025]: "Parametric design enables iterative and customizable design approaches" using Grasshopper and Rhino3D for computational textile pattern development. However, research revealed critical adoption barriers:

1. **Tool Complexity**: Parametric definitions (nodes and connections) don't match fashion design cognitive patterns (sketches and draping)
2. **Iteration Speed**: Computational pattern generation can be **slower than manual drafting** for simple modifications
3. **Abstraction Gap**: Mental model required to operate tools differs from mental model used for creative design

**Fashion Designer Workflow Requirements**:
- **<5 second iteration cycles** to support creative exploration (not 30+ seconds)
- **Immediate visual feedback**: Change pattern → see drape update instantly
- **Progressive complexity**: Simple tasks easy (adjust fabric from preset library), complex tasks possible (direct physics parameter editing)

These requirements establish hard constraints: virtual try-on systems must provide <5 second total latency (pattern import + simulation + rendering + display) to be viable design tools.

**Interpretability Requirements** [Ryu & Lee 2025]: Generative AI for fashion design study revealed:

**Key Finding**: DALL-E 3 achieved **67.6% perfect implementation** when generating fashion illustrations from prompts
- **Success Factor**: "Expertly worded prompts are necessary for accurate fashion design implementation"
- **Critical Limitation**: Struggled with **trend elements like gender fluidity** and haute couture complexity
- **Designer Role**: Fashion expertise remains central—AI cannot infer cultural context or emotional resonance from data alone

**Implications for 3D Drape Simulation**:
If 2D image generation requires expert prompt engineering to achieve ~68% accuracy, **3D fabric drape simulation** with vastly larger parameter spaces (fabric mechanics, body geometry, pose dynamics) will require even more sophisticated designer guidance.

**The Black Box Problem Extended**:
Fashion designers need to understand:
- **Why**: "Why did the simulation produce pulling at the shoulder seam?" (Causality)
- **What-if**: "Which fabric parameter adjustment would reduce bunching at the waist?" (Sensitivity)
- **Trust**: "Is this drape artifact a physics simulation error or accurate fabric behavior?" (Validity)

Current 4DGS methods provide no interpretability mechanisms. Ryu & Lee's work emphasizes that tools must **amplify designer expertise**, not attempt to replace it with black-box optimization. This principle applies equally to virtual try-on: systems must explain decisions, not just render outcomes.

**Sustainability Metrics** [MDPI 2025]: Digital technologies in sustainable textile development literature review identifies virtual prototyping as critical sustainability enabler:

**Sample Waste Reality**:
- Physical pattern development generates **15-30% fabric waste** (cutting errors, fit adjustments)
- Typical garment requires **3-5 fit samples** before production approval
- Each sample consumes fabric that becomes waste if pattern changes

**Virtual Prototyping Value Proposition**:
- "Multiple iterations without consuming physical materials"
- Enables rapid exploration of design variations without physical waste
- Digital Product Creation (DPC) uses virtual environments to "conceptualize, design, develop, and manufacture 3D products"

**Quantified Impact** (medium-size fashion brand example):
- 200 styles/season × 4 fit samples/style × 2 meters fabric/sample = **1,600 meters fabric**
- Virtual try-on (80% elimination): Save 1,280 meters fabric
- Cotton @ 2,700 L water/kg, 200 g/m²: **692,000 liters water saved per season**
- Additional: CO₂ from shipping samples, time-to-market acceleration, customization enablement

**Critical Success Factor**: This sustainability value only realizes if **designers trust simulation enough to eliminate physical samples**. Trust requires:
- **Accuracy**: ±5-10mm tolerance validated against physical garments
- **Reliability**: Simulation must work consistently across fabric types, body shapes, garment styles
- **Interpretability**: Designers must understand why simulation predicts specific fit issues
- **Speed**: <5 second iteration cycles to support design exploration

The fashion technology community is asking: **Can we trust digital simulation enough to eliminate physical samples?** Computer vision research must engage with this question as manufacturing validation challenge, not merely rendering quality optimization.

---

## 3. The Virtual Try-On Validation Gap

### 3.1 Problem Definition: Fashion vs. Computer Vision Perspectives

**Virtual try-on for manufacturing validation** requires answering:

> "Given a manufacturing-ready 2D pattern and a 3D body scan of a novel individual, does the simulated 4DGS drape accurately predict how the physical garment would fit?"

This differs fundamentally from computer vision novel view synthesis:

| Aspect | Computer Vision Focus | Fashion Practitioner Focus |
|--------|----------------------|---------------------------|
| **Success Metric** | Novel view synthesis quality (PSNR, SSIM) | Manufacturing fit accuracy (±5-10mm tolerance) |
| **Validation** | Visual similarity to video frames | Match to physical garment on real body |
| **Generalization** | Unseen camera viewpoints | Unseen body shapes and fabric types |
| **Speed** | Real-time rendering (30-60 FPS) | Acceptable iteration time (<5 sec/cycle) |
| **Deliverable** | Photorealistic video | Manufacturing-ready pattern validation |

**Key Constraint**: You **cannot modify the person's body shape** to improve fit. The simulation must accurately model how this specific fabric drapes on this specific body geometry.

### 3.2 Why Learned Models Fail: The Generalization Problem

D3GA and 3DGS-Avatar train neural networks mapping poses → garment deformations using person-specific training data. Sun et al.'s [2025] review of deep learning for 3D garment generation identifies three fundamental failure modes:

**Failure Mode 1: Extrapolation Failure**
- Models trained on fitted clothing fail on loose-fitting garments
- No mechanism to transfer to different body geometry
- Visual plausibility ≠ physical accuracy

**Failure Mode 2: Fabric Generalization Failure**
- Cannot adapt to novel fabric types (e.g., model trained on wovens fails on knits)
- Networks learn correlations, not physics laws
- No fabric material properties constrain predictions

**Failure Mode 3: Body Shape Generalization Failure**
- Cannot accurately predict drape on body proportions outside training distribution
- 3DGS-Avatar explicitly acknowledges: "difficulty with extreme out-of-distribution poses"
- D3GA requires per-frame garment templates for long loose garments

**Implications for Virtual Try-On**:
- Cannot validate pattern fit across size grading (XS to XXL)
- Cannot simulate garment on customer's body scan for customization
- Cannot A/B test different fabrics' drape characteristics

### 3.3 Why Physics-Based Methods Remain Unvalidated

MPMAvatar models anisotropic fabric mechanics and claims "zero-shot generalizable to interactions with an unseen external object." Yet the paper never evaluates body shape diversity, never tests virtual try-on scenarios, never validates against physical garment fit.

**Possible Reasons**:

1. **Performance Gap**: 1.1 seconds/frame vs <5 second requirement for designer workflows [Digital Creativity 2025]
2. **Validation Complexity**: Requires ground-truth physical garments on multiple body shapes
3. **Research Community Focus**: Graphics prioritizes visual quality metrics, not manufacturing fit accuracy
4. **Manufacturing CAD Disconnect**: Physics simulators expect triangle meshes, not 2D DXF patterns

### 3.4 Body Shape Generalization: The Manufacturing Imperative

Oh & Kim [2025] emphasize that computational pattern generation must accommodate **diverse body types**, not merely average forms. Their landmark matching algorithm highlights a critical requirement: patterns must adapt to individual anthropometric variations while preserving style lines and manufacturing constraints.

**Fashion Industry Validation Standards**:
While computer vision validates 4DGS with novel view synthesis metrics, fashion practitioners require:
- **Fit tolerance**: ±5-10mm accuracy across critical fit points (bust, waist, hip, shoulder)
- **Size range validation**: XS to 3XL, accommodating proportional variations
- **Diverse body testing**: Different torso lengths, shoulder widths, spinal curvatures

Oh & Kim validated their algorithm by comparing generated patterns against **commercial pattern company standards** and **physical garment construction**—not just virtual similarity metrics. This establishes a key principle: **virtual try-on validation requires physical garment comparison**.

### 3.5 The "Expertly Worded Prompts" Problem: Interpretability for Designers

Ryu & Lee's [2025] study revealed that DALL-E 3 achieved 67.6% perfect implementation when generating fashion illustrations—and crucially, that **"expertly worded prompts are necessary for accurate fashion design implementation, highlighting the important role of fashion experts."**

If 2D image generation requires expert prompt engineering to achieve ~68% accuracy, **3D fabric drape simulation** with its vastly larger parameter space will require even more sophisticated designer guidance.

**The Black Box Problem**: Current 4DGS methods provide no interpretability:
- Why did the simulation produce pulling at the shoulder seam?
- Which fabric parameter adjustment would reduce bunching at the waist?
- Is this drape artifact a physics simulation error or accurate fabric behavior?

**Design Pattern for Interpretable Simulation**:
1. **Visual debugging layers**: Highlight regions where fabric stress exceeds material limits
2. **Parameter sensitivity visualization**: Show how adjusting fabric stiffness affects drape
3. **Constraint violation indicators**: Flag when simulation violates physical laws
4. **Comparative visualization**: Side-by-side comparison of different fabric choices on same body

---

## 4. Manufacturing CAD Integration

### 4.1 The Pattern-to-Drape Pipeline

**Input**: Manufacturing-ready 2D pattern from neurosymbolic CAD
- DXF file format with AAMA/ASTM annotations
- Seam matching pairs (±3% tolerance validated)
- Grain line directions (±2° alignment validated)
- Notches, darts, construction sequence

**Challenge 1: Fabric Parameter Translation**

Fashion CAD systems use **non-standardized fabric parameter representations**:

| CAD System | Stretch Model | Bending Model | Database Format |
|------------|--------------|---------------|-----------------|
| CLO3D | Strain-stress curves | Bending rigidity | Custom XML |
| Browzwear | Elasticity modulus | Bending stiffness | U3M format |
| Optitex | Stretch percentage | Flexibility index | Proprietary |
| **MPMAvatar** | **Young's modulus** | **Material stiffness tensor** | **Physics units** |

**The Interoperability Problem**: A cotton twill fabric has **one set of physical properties** but requires **four different parameter representations**.

**Critical Research Direction**: Develop **bidirectional translation layer**:
```
CLO3D fabric parameters ↔ MPM physics parameters ↔ Browzwear U3M format
```

Validation requirement: **parameter translation must preserve drape behavior**.

### 4.2 Designer Workflow Integration

**Tool Complexity vs. Design Thinking** [Digital Creativity 2025]: Parametric definitions (nodes and connections) don't match fashion design cognitive patterns (sketches and draping). This creates an **abstraction gap**.

**Iteration Speed Requirements**: Computational pattern generation can be slower than manual drafting for simple modifications. Fashion designers require **<5 second iteration cycles** to support creative exploration.

**Progressive Complexity Principle**: Successful tools make "simple tasks easy, complex tasks possible":
- **Novice mode**: Adjust fabric from preset library, see immediate drape update
- **Intermediate mode**: Tune fabric parameters with visual sliders + real-time preview
- **Expert mode**: Direct physics parameter specification for edge cases

**Integration with Existing Workflows**: Fashion designers already use CLO3D, Browzwear, Optitex. Research priority: **4DGS as backend rendering engine** for existing CAD tools, not standalone replacement.

### 4.3 World Model Architecture Adaptation

Ctrl-World's [Guo et al. 2025] architecture offers promising patterns for cloth simulation:

**Multi-View Joint Prediction for Contact-Rich Interactions**:
- Single-view reconstruction may hallucinate plausible drape violating physical constraints
- Multi-view consistency enforces geometric accuracy at garment-body contact zones (seams, waistbands)
- **Fashion Application**: Joint prediction across front/back/side views reduces hallucination

**Frame-Level Conditioning for Fine-Grained Control**:
- Centimeter-level controllability through pose-conditioned per-frame synthesis
- **Fashion Requirement**: Millimeter-level precision for seam allowances, dart placement
- Suggests garment drape simulation requires similarly fine-grained conditioning on body pose and fabric properties

**Pose-Conditioned Memory for Temporal Consistency**:
- Prevents prediction error accumulation over long-horizon rollouts
- **Fashion Challenge**: Garments must maintain wrinkle patterns across pose sequences
- Fabric stretch must recover when pose returns to rest position

**Open Challenges for Cloth World Models**:
- **Anisotropic mechanics**: Fabric stretches differently in warp vs. weft directions
- **Large deformations**: Garments undergo buckling, folding, self-contact
- **Material diversity**: Cotton twill vs. silk charmeuse exhibit vastly different drape
- **Body shape variability**: Must generalize to unseen body geometries, not just unseen object configurations

---

## 5. Research Priorities and Technical Specifications

### 5.1 Four-Level Validation Framework

Fashion practitioners require **manufacturing validity**, not just visual plausibility. We propose a hierarchical validation framework:

**Level 1: Virtual-to-Virtual Validation** (baseline sanity checks)
- Metric: Does simulated drape match reference CAD tool (CLO3D) within tolerance?
- Threshold: <2% area difference in 2D pattern projection
- Limitation: Validates consistency, not physical accuracy

**Level 2: Virtual-to-Physical Validation** (manufacturing grade)
- Metric: Simulated drape vs. physical garment on same mannequin/body scan
- Measurement protocol:
  - 3D scan physical garment on mannequin
  - Compare scan mesh to simulated 4DGS geometry
  - Compute point-to-surface distance at critical fit points
- Threshold: **±5-10mm at bust, waist, hip, shoulder**
- Critical zones: Seam lines, dart endpoints, hem curves

**Level 3: Body Shape Generalization Validation** (virtual try-on capability)
- Metric: Simulation accuracy across diverse body shapes
- Test protocol:
  - Same garment pattern, 10-15 different body scans (XS-3XL size range)
  - Construct physical garments, photograph on actual bodies
  - Compare 4DGS rendering to photographic ground truth
- Threshold: Maintain ±10mm tolerance across 80% of body shape test set

**Level 4: Designer Decision-Making Validation** (practical utility)
- Metric: Does simulation enable correct design decisions?
- Test protocol:
  - Designer identifies fit issues in virtual try-on
  - Adjusts 2D pattern based on simulation feedback
  - Construct physical garment from adjusted pattern
  - Measure: Did pattern adjustment resolve fit issue?
- Success criterion: 80% of simulation-identified issues are real (not simulation artifacts)

**Why This Hierarchy Matters**:
- Computer vision metrics (Level 1) are necessary but not sufficient
- Manufacturing validity (Level 2-3) requires physical garment comparison
- Practical utility (Level 4) validates that simulation **informs better design decisions**

### 5.2 Hybrid Physics-Learning Architecture

**Challenge**: MPMAvatar achieves physics-based generalization but 1.1 sec/frame is too slow for <5 sec designer iteration requirement.

**Proposed Solution**: Hybrid approach
1. **Coarse physics simulation**: MPM at reduced resolution for physical plausibility
2. **Neural upsampling**: Learned refinement to photorealistic quality
3. **Multi-view conditioning**: Ctrl-World pattern for contact-rich interaction accuracy

**Target Performance**: <5 seconds total (coarse sim 3 sec + neural upsampling 1 sec + rendering 1 sec)

### 5.3 Standardized Fabric Property Database

**Current Problem**: No standardized fabric database works across CAD tools and physics simulators.

**Proposed Solution**: Open-source fabric property database with:
- **Measured properties**: ASTM D1388 stiffness, KES shear/tensile, drape coefficient
- **Multi-format export**: CLO3D XML, Browzwear U3M, MPM physics parameters
- **Validation protocol**: Each fabric includes reference drape video for visual validation
- **Initial coverage**: 50 common fabrics (cotton twill, silk charmeuse, denim, jersey, etc.)

**Sustainability Impact**: Standardized fabric libraries reduce need for physical swatch sampling.

### 5.4 Skill Development and Designer Training

Fashion education research [Fashion & Textiles 2025] on 3D-to-2D fit correction skills revealed: **Seeing a fit issue in 3D simulation ≠ knowing how to fix the 2D pattern**.

**Implications for System Design**:

1. **Visual Causality Explanation**: When simulation shows pulling at shoulder seam:
   - Highlight pattern region causing issue (shoulder dart, armscye curve)
   - Suggest parameter adjustments ("Increase shoulder dart intake by 5mm")
   - Show predicted outcome of adjustment (live preview)

2. **Guided Learning Mode**: For students/novice designers:
   - "This bunching at waist suggests insufficient dart suppression. Try: [Show adjustment]"
   - Progressive disclosure: Simple fixes first, advanced techniques for edge cases
   - Confidence scoring: "85% confident this adjustment will resolve issue"

3. **Expert Validation Tools**: For experienced pattern makers:
   - Direct physics parameter editing
   - Comparative visualization (different fabric choices side-by-side)
   - Batch testing (validate pattern across size range automatically)

**Research Priority**: User studies measuring:
- Time to identify fit issues: Virtual try-on vs. physical muslin fitting
- Accuracy of pattern corrections: Simulation-guided vs. traditional methods
- Designer confidence: "I trust this simulation to make production decisions" (Likert scale)

### 5.5 Missing Research: The Validation Dataset

NO PUBLIC DATASET exists for:
- Same garment (with known 2D pattern) on multiple body shapes
- Ground-truth 3D scans of draped garment on each body
- Measured fabric material parameters
- Manufacturing specifications (seam allowances, grain lines)

**Proposed Dataset Requirements**:
- 10 garments (varying fabric types: woven, knit, etc.)
- 20 body shapes (covering anthropometric diversity)
- 3D scans: garment on mannequin + garment on each body
- Material properties: ASTM D1388 stiffness, KES shear/tensile
- Patterns: DXF files with seam allowances, grain markings

**Challenges**:
- **Cost**: 200 garment-body combinations × 3D scanning (estimated $50-100/scan)
- **Privacy**: Body scans require consent, anonymization protocols
- **Reproducibility**: Fabric properties change with washing, storage conditions
- **Standardization**: Pose, lighting, scan resolution must be controlled across all captures

**Mitigation Strategies**:
1. **Phased Approach**: Start with 3 garments × 10 body shapes pilot (30 scans)
2. **Synthetic Augmentation**: Use validated physics simulation to generate additional training data
3. **Crowdsourcing**: Partner with fashion design programs for distributed data collection
4. **Open Science**: Pre-register protocols, share raw data for community validation

Without this dataset, virtual try-on claims remain unvalidated.

### 5.6 Fabric Property Measurement Protocols

**Current Problem**: Fashion CAD tools and physics simulators use different fabric property representations with no standardized measurement protocols bridging them.

**Proposed Solution**: Standardized fabric characterization pipeline

**Stage 1: Physical Measurement**
- **ASTM D1388**: Cantilever test for bending rigidity
- **KES-F System**: Kawabata Evaluation System measuring tensile, shear, bending, compression, surface properties
- **Drape Coefficient**: ASTM D1388 standard using circular fabric sample draped over pedestal
- **Weight/Thickness**: Basic metrics affecting simulation parameters

**Stage 2: CAD Tool Calibration**
- Import fabric into CLO3D, Browzwear, Optitex
- Adjust tool-specific parameters until virtual drape matches physical drape coefficient
- Record calibrated parameter sets for each tool

**Stage 3: Physics Parameter Derivation**
- Map measured properties to MPM simulation parameters:
  - Bending rigidity → Bending stiffness tensor
  - KES tensile → Young's modulus (warp/weft directions)
  - KES shear → Shear modulus
- Validate: physics simulation should match physical drape coefficient

**Stage 4: Cross-Validation**
- Same fabric simulated in CLO3D, MPM, and Browzwear
- Drape outcomes should be visually similar
- Quantify divergence: if >10% difference, revisit parameter mapping

**Deliverable**: Open-source fabric database with:
- Physical measurements (ASTM/KES values)
- CAD tool parameters (CLO3D XML, Browzwear U3M)
- Physics parameters (MPM Young's modulus, Poisson's ratio)
- Reference drape videos for visual validation

**Initial Coverage**: 50 common fabrics (cotton twill, denim, silk charmeuse, wool flannel, polyester knit, etc.)

### 5.7 Real-World Deployment Considerations

**Manufacturing Integration Requirements**:

1. **Pattern Import/Export Workflows**:
   - DXF → Physics simulation must preserve notches, grain lines, seam allowances
   - Simulation → DXF export must maintain sewability (no mesh artifacts)
   - Bidirectional iteration: Designer adjusts pattern → re-simulate → verify fit

2. **Size Grading Validation**:
   - Fashion brands produce 8-12 sizes from single pattern
   - Virtual try-on must validate **entire size range**, not single size
   - Batch processing: Simulate pattern on 12 body models (XS-3XL) automatically
   - Report: "Pattern fits sizes S-L correctly; XS shows pulling at shoulder, XL shows excess ease at waist"

3. **Customization Workflows**:
   - Customer provides body scan (via mobile app or in-store scanner)
   - System generates custom pattern from base pattern + measurements
   - Virtual try-on validates custom pattern fit before fabric cutting
   - Threshold: Must achieve 90% fit success rate to justify elimination of physical try-on

4. **Quality Assurance Integration**:
   - Existing fashion QA checks fit on physical samples
   - Virtual try-on must integrate with QA protocols
   - Acceptance criteria: If simulation says "fit OK," physical garment must fit 95% of time
   - Failure analysis: When simulation fails, identify root cause (fabric parameter error? Body scan quality? Physics solver limitation?)

**Business Model Implications**:

- **Upfront Cost**: Fabric measurement, dataset creation, system integration
- **Ongoing Cost**: Computational infrastructure (GPU clusters for batch simulation)
- **Value Proposition**: Sample elimination savings must exceed system costs
- **Break-even**: For 200 styles/season × 4 samples × $50 fabric/sample = $40,000 fabric cost
  - Virtual try-on system must cost <$40k/year to break even on fabric alone
  - Additional value: Faster time-to-market, customization enablement, return reduction

---

## 6. Discussion: Bridging Communities

### 6.1 Computer Science vs. Fashion Research Priorities

**Critical Tension**: Computer science 4DGS research and fashion technology research are asking complementary questions but rarely collaborating.

**Where Collaboration Is Essential**:

1. **Physics-Based Simulation**:
   - CS: Develop efficient MPM/FEM solvers, GPU acceleration
   - Fashion: Provide fabric property measurement protocols, validation datasets
   - **Collaboration**: Map CAD fabric parameters to simulation physics with validated translation

2. **Body Shape Representation**:
   - CS: SMPL-X, parametric body models, pose estimation
   - Fashion: Anthropometric measurement protocols, fit standards, body diversity
   - **Collaboration**: Ensure body models match industry fit testing requirements

3. **Validation Methodology**:
   - CS: Benchmark datasets, quantitative metrics, reproducible evaluation
   - Fashion: Physical garment construction, wear testing, designer feedback
   - **Collaboration**: Hybrid validation combining simulation accuracy and manufacturing reality

4. **Interface Design**:
   - CS: Real-time rendering, GPU optimization, neural acceleration
   - Fashion: Designer workflow, creative process understanding, tool adoption barriers
   - **Collaboration**: Leverage technical capabilities within designer workflows

**Recommendations for Research Community**:

1. **Partner with Fashion Design Programs**: User studies with actual designers, not just CS researchers
2. **Publish in Fashion Technology Venues**: Share results in Clothing and Textiles Research Journal, Fashion and Textiles
3. **Develop Industry-Relevant Benchmarks**: Not just novel view synthesis, but fit accuracy on diverse body shapes
4. **Quantify Sustainability Impact**: Samples eliminated, waste reduced, customization enabled
5. **Open-Source Fabric Property Databases**: Enable reproducible research and CAD tool interoperability

### 6.2 The Sustainability Imperative

Fashion sustainability research [MDPI 2025] identifies virtual prototyping as critical for:

**Sample Waste Reduction**:
- Physical pattern development generates 15-30% fabric waste
- Typical garment requires 3-5 fit samples before production
- Virtual try-on potential: **Eliminate 60-80% of fit samples**

**Quantifiable Sustainability Metrics**:
- **Fabric saved**: (# patterns × # fit samples × avg fabric per sample) × elimination rate
- **Water saved**: Fabric yardage × water consumption per yard (cotton: ~2,700 liters/kg)
- **CO₂ reduced**: Shipping samples (pattern → production → fitting → revision → repeat)

**Example Calculation** (medium-size fashion brand):
- 200 styles/season × 4 fit samples/style × 2 meters fabric/sample = 1,600 meters fabric
- Virtual try-on (80% elimination): Save 1,280 meters fabric
- Cotton @ 2,700 L water/kg, 200 g/m²: **692,000 liters water saved per season**
- Plus: CO₂ from shipping, time-to-market acceleration, customization enablement

**Critical Success Factor**: Sustainability benefits only realize if **designers trust simulation enough to eliminate physical samples**. This returns to validation requirement: ±5-10mm accuracy threshold must be demonstrated through physical garment comparison.

---

## 7. Conclusion

The fashion industry confronts an urgent need for virtual try-on technology that serves not just marketing visualization but **manufacturing validation**. Current 4DGS methods achieve photorealistic rendering yet fail the critical test: **Can simulation accurately predict garment fit on diverse body shapes with ±5-10mm tolerance?**

Our analysis reveals fundamental gaps:

1. **Learned models** (D3GA, 3DGS-Avatar) train person-specific networks incompatible with body shape generalization
2. **Physics-based models** (MPMAvatar) have the theoretical foundation for generalization but lack virtual try-on validation
3. **World model architectures** (Ctrl-World) offer promising patterns for contact-rich interactions and fine-grained control, but cloth-specific challenges remain
4. **Fashion practitioners** require interpretable simulation with <5 second iteration cycles, not black-box optimization
5. **Sustainability impact** (~700,000 liters water saved per season) only realizes through manufacturing-grade accuracy enabling physical sample elimination

**Research Priorities**:

- **Four-level validation framework**: From virtual-virtual consistency to designer decision-making utility
- **Hybrid physics-learning architecture**: Combining MPM generalization with neural acceleration
- **Standardized fabric property database**: Open-source, multi-format, validated against physical drape
- **CAD tool integration**: 4DGS as backend rendering engine within existing designer workflows
- **Public validation dataset**: Same garments on multiple body shapes with measured fabric properties

**The Collaboration Imperative**: Success requires bridging computer vision research (efficient physics simulation, photorealistic rendering) and fashion technology (manufacturing validity, designer workflows, sustainability metrics). Fashion researchers aren't asking for incremental improvements to graphics algorithms—they're asking: **Can we trust digital simulation enough to eliminate physical samples?**

That's the research question this community must answer. The technical capabilities exist; the validation, integration, and practitioner trust remain to be established.

---

## Acknowledgments

This work builds on companion research examining DPP infrastructure, manufacturing-valid pattern generation, and physics-based drape simulation. We thank the fashion design and textile engineering communities for establishing practical requirements that ground this technical research in manufacturing reality.

---

## References

### Core 4DGS Methods

Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. (2023). 3D Gaussian Splatting for Real-Time Radiance Field Rendering. *ACM Transactions on Graphics*, 42(4).

Wu, G., Yi, T., Fang, J., Xie, L., Zhang, X., Wei, W., Liu, W., Tian, Q., & Wang, X. (2024). 4D Gaussian Splatting for Real-Time Dynamic Scene Rendering. *CVPR*.

Rong, Y., et al. (2024). Gaussian Garments: Reconstructing Simulation-Ready Clothing with Photorealistic Appearance from Multi-View Video. *3DV 2025*.

Wang, R., et al. (2025). ClothingTwin: High-Fidelity Clothing Reconstruction from 3D Human. *arXiv:2501.14056*.

Zielonka, W., Bagautdinov, T., Saito, S., Zollhöfer, M., Thies, J., & Romero, J. (2023). Drivable 3D Gaussian Avatars (D3GA). *ICCV 2023*.

Qian, S., Kirschstein, T., Schoneveld, L., Davoli, D., Giebenhain, S., & Nießner, M. (2024). 3DGS-Avatar: Animatable Avatars via Deformable 3D Gaussian Splatting. *CVPR 2024*.

Lee, H., Kim, T., & Lee, S. (2025). MPMAvatar: Physics-based Reconstruction and Rendering of Animatable Clothed Human with Material Point Method. *SIGGRAPH 2025*.

Miao, Y., Mu, L., Yu, L., & Han, X. (2025). Offset Gaussian Contacts for Physically-based Character Skinning and Clothing Simulation. *arXiv:2501.03386*.

### Fashion Technology Research

Ryu, C., & Lee, Y. K. (2025). Effective Fashion Design Collection Implementation with Generative AI: ChatGPT and Dall-E. *Clothing and Textiles Research Journal*. DOI: 10.1177/0887302X251348003

Oh, J., & Kim, S. (2025). Generation of Body-Fit Garment Patterns Using a Landmark Matching Algorithm. *Clothing and Textiles Research Journal*. DOI: 10.1177/0887302X251340652

Sun, Y., Hao, Z., Wang, Z., Jin, J., Ye, Q., & Lyu, Y. (2025). Deep learning for 3D garment generation: A review. *Textile Research Journal*. DOI: 10.1177/00405175251335188

Parametric pattern design for manually knitted textile panels. (2025). *Digital Creativity*. DOI: 10.1080/14626268.2025.2514120

Developing an instrument with simulations to measure 3D to 2D fit correction skills in fashion design. (2025). *Fashion and Textiles*. DOI: 10.1186/s40691-025-00417-y

Digital Technologies in the Sustainable Design and Development of Textiles and Clothing—A Literature Review. (2025). *Sustainability*, 17(4), 1371. DOI: 10.3390/su17041371

### World Models and Robotics

Guo, Y., Shi, L. X., Chen, J., & Finn, C. (2025). Ctrl-World: A Controllable Generative World Model for Robot Manipulation. *arXiv:2510.10125*. https://arxiv.org/html/2510.10125v2

### CAD and Manufacturing

Xiang, R., et al. (2024). GarmentCode: Programming Parametric Sewing Patterns. *arXiv:2404.16891*.

Zhou, R., et al. (2024). Design2GarmentCode: Turning Design Concepts to Tangible Garments Through Program Synthesis. *arXiv:2412.08603*.

---

**Version**: v2 - Fashion Research Integration
**Date**: October 2025
**Word Count**: ~6,800 words
**File Size**: ~50kB
**Status**: Ready for review and further refinement
