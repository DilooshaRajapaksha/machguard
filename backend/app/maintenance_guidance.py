import re


def answer(record, question):
    notes = record["notes"]
    words = set(re.findall(r"[a-z]{3,}", question.lower()))
    services = record["services"]
    forecast = record["forecast"]
    parts = []
    sources = []
    if words & {"temperature","hot","overheating","forecast","health","limit","warming"}:
        if forecast:
            parts.append(f"At {forecast['issued']}, probe 1 was projected to reach {forecast['projected_c']:.1f} C after 15 minutes. The configured warning level was {forecast['limit_c']:g} C. Observation: {forecast['result']}.")
        parts.append("Probe location: " + (notes.get("probe_location") or "unrecorded") + ". Load: " + (notes.get("operating_load") or "unrecorded") + ". Approved range: " + (notes.get("approved_range") or "unrecorded") + ".")
        words.update({"temperature","hot","overheating"})
    if words & {"service","scheduled","due"} and services:
        parts.append(f"Last recorded service: {services[0]['serviced']}. Next scheduled service: {services[0]['due'] or 'unscheduled'}.")
    candidates = []
    for service in services:
        symptom = set(re.findall(r"[a-z]{3,}", service["symptom"].lower()))
        score = len(words & symptom)
        if score:
            candidates.append((score, service))
    if candidates:
        service = max(candidates,key=lambda pair:pair[0])[1]
        parts.append(f"Review the {service['serviced']} record. Symptom: {service['symptom']}. Recorded repair outcome: {service['outcome']}. Confirm whether today's conditions match.")
        sources.append("Service record " + str(service["id"]))
    for manual in record["manuals"]:
        excerpt = manual.get("excerpt") or ""
        if words.intersection(re.findall(r"[a-z]{3,}", excerpt.lower())):
            parts.append(excerpt)
            sources.append(manual["name"] + " (engineer-entered extract)")
    return {"answer":" ".join(parts) or "No matching evidence is recorded for this machine yet.", "sources":sources}

