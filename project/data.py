# project/data.py
# Contains static data for the application.

AWARENESS_DATA = {
    "quality_safety": [
        {'test': 'Appearance & Color', 'purpose': 'Quick indication of freshness, purity, and spoilage.', 'significance': 'Important for consumer acceptance'},
        {'test': 'Physical State', 'purpose': 'Check uniformity, ensure free from clots, sediments, or extraneous matter.', 'significance': 'Indicates freshness & proper handling'},
        {'test': 'Odor & Flavor', 'purpose': 'Detect freshness, spoilage, contamination, feed effects, or chemical adulteration.', 'significance': 'Critical for safety & consumer acceptance'},
        {'test': 'Taste', 'purpose': 'Confirm freshness, absence of off-flavors, spoilage, or adulteration.', 'significance': 'Ensures acceptability for consumers'},
        {'test': 'Fat & SNF %', 'purpose': 'Measure milk fat & solids-not-fat.', 'significance': 'Ensures authenticity, nutrition, compliance & fair trade'},
        {'test': 'Protein %', 'purpose': 'Measure protein content.', 'significance': 'Confirms authenticity, nutrition (growth & repair), processing quality & fair trade'},
        {'test': 'Acidity % (LA)', 'purpose': 'Titratable acidity test.', 'significance': 'Indicates freshness, microbial quality, and heating/boiling suitability'},
        {'test': 'Heat Stability', 'purpose': 'Check stability during heating.', 'significance': 'Ensures product quality & shelf life'},
        {'test': 'Heat Stability (Alcohol Test)', 'purpose': 'Check protein stability.', 'significance': 'Detects abnormal/spoiled milk; ensures suitability for boiling/heating'},
        {'test': 'COB (Clot on Boiling)', 'purpose': 'Test for curdling on boiling.', 'significance': 'Detects high acidity, spoilage, or mastitis milk'},
        {'test': 'MBRT', 'purpose': 'Methylene Blue Reduction Test.', 'significance': 'Indicates microbial load; ensures safety, freshness & shelf life'},
        {'test': 'Phosphatase Test', 'purpose': 'Verify pasteurization.', 'significance': 'Confirms safety from harmful pathogens'}
    ],
    "adulteration": [
        {'test': 'Cane Sugar Test', 'purpose': 'Detect added sugar.', 'significance': 'Ensures authenticity, legal compliance & health safety (diabetes risk)'},
        {'test': 'Salt Test', 'purpose': 'Detect added salt.', 'significance': 'Ensures authenticity, legal compliance & health safety'},
        {'test': 'Starch Test', 'purpose': 'Detect starch adulteration.', 'significance': 'Prevents digestive issues; ensures authenticity & compliance'},
        {'test': 'Urea Test', 'purpose': 'Detect added urea (to increase SNF).', 'significance': 'Prevents health hazards; ensures authenticity'},
        {'test': 'Maltodextrin Test', 'purpose': 'Detect maltodextrin addition.', 'significance': 'Ensures authenticity & legal compliance'},
        {'test': 'Formalin Test', 'purpose': 'Detect formalin preservative.', 'significance': 'Toxic & unsafe; ensures health safety'},
        {'test': 'Hydrogen Peroxide Test', 'purpose': 'Detect hydrogen peroxide preservative.', 'significance': 'Illegal & harmful to health'},
        {'test': 'Neutralizers Test', 'purpose': 'Detect neutralizing chemicals.', 'significance': 'Unsafe; indicates violation of standards'},
        {'test': 'Glucose Test', 'purpose': 'Detect added glucose.', 'significance': 'Prevents health impact & adulteration masking'},
        {'test': 'Detergent Test', 'purpose': 'Detect detergents.', 'significance': 'Highly toxic; indicates serious adulteration'},
        {'test': 'Ammonium Sulphate Test', 'purpose': 'Detect ammonium sulphate (used to raise SNF).', 'significance': 'Unsafe; affects health'},
        {'test': 'Fat B.R. Reading at 40°C', 'purpose': 'Measure milk fat purity.', 'significance': 'Detects adulteration with foreign fats'},
        {'test': 'Total Sodium', 'purpose': 'Measure sodium content.', 'significance': 'Detects abnormal milk; ensures safety & compliance'}
    ]
}
