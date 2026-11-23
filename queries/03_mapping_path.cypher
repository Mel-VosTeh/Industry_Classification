:param system => 'FIC_A';
:param code => 'A11';
// A mapping followed by an incoming hierarchy edge; this is NOT equivalence.
MATCH path = (s:ClassificationCode {system: $system, code: $code})
             -[:MAPS_TO]->(target)<-[:PARENT_OF]-(parent)
RETURN path;
