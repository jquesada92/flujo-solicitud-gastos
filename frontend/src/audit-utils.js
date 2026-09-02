const CHANGE_TYPE_NAMES = {
  CREATE: "Creación",
  UPDATE: "Actualización",
  DELETE: "Eliminación",
};

function calendarDateParts(value, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  return Object.fromEntries(parts.map(({ type, value: part }) => [type, part]));
}

function utcCalendarDate(year, month, day) {
  return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
}

function dateInputValue(value) {
  return [
    value.getUTCFullYear(),
    String(value.getUTCMonth() + 1).padStart(2, "0"),
    String(value.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

export function defaultAuditDateRange(
  reference = new Date(),
  timeZone = "America/Panama",
) {
  const { year, month, day } = calendarDateParts(reference, timeZone);
  const dateTo = utcCalendarDate(year, month, day);
  const dateFrom = new Date(dateTo);
  dateFrom.setUTCDate(dateFrom.getUTCDate() - 6);
  return {
    dateFrom: dateInputValue(dateFrom),
    dateTo: dateInputValue(dateTo),
  };
}

export function auditChangeTypeName(value) {
  return CHANGE_TYPE_NAMES[String(value || "").toUpperCase()] || "Cambio";
}

function objectLabel(value) {
  if (value.name) return String(value.name);
  if (value.code) return String(value.code);
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${auditValueText(item, key)}`)
    .join(" · ");
}

export function auditValueText(value, field = "") {
  if (value === null || value === undefined || value === "") return "Sin valor";
  if (typeof value === "boolean") {
    if (field === "active") return value ? "Activo" : "Inactivo";
    return value ? "Sí" : "No";
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return "Ninguno";
    return value
      .map((item) => (
        item && typeof item === "object" ? objectLabel(item) : auditValueText(item, field)
      ))
      .join(", ");
  }
  if (typeof value === "object") return objectLabel(value) || "Sin valor";
  return String(value);
}

export function auditChangeEntries(event) {
  const changes = event?.changes && typeof event.changes === "object" ? event.changes : {};
  const orderedFields = [
    ...(event?.changed_fields || []),
    ...Object.keys(changes),
  ].filter((field, index, fields) => field && fields.indexOf(field) === index);

  return orderedFields
    .filter((field) => changes[field] && typeof changes[field] === "object")
    .map((field) => ({
      field,
      before: changes[field].before,
      after: changes[field].after,
    }));
}
