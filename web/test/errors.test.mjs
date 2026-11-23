import test from "node:test";
import assert from "node:assert/strict";
import { explain, dateOrderQuestion, ordinal } from "../src/errors.js";

test("every core error code has its own voice", () => {
  const codes = ["too_few_messages", "not_two_people", "unrecognized_format", "bad_archive", "inconsistent_dates", "no_chat"];
  const titles = codes.map((code) => explain({ code, data: {} }).title);
  assert.equal(new Set(titles).size, codes.length, "each code should have a distinct title");
  assert.ok(titles.every((t) => t.length > 5));
});

test("the trailer and the cast jokes use the real numbers", () => {
  assert.match(explain({ code: "too_few_messages", data: { count: 12 } }).body, /12 messages/);
  assert.match(explain({ code: "not_two_people", data: { names: ["a", "b", "c", "d", "e", "f"] } }).title, /^6 people\?/);
});

test("an unknown error never leaks a stack trace into the headline", () => {
  const e = explain({ code: "internal", message: "TypeError: boom at line 4" });
  assert.equal(e.title, "Something broke on our side.");
  assert.match(e.body, /still only in this tab/);
  assert.equal(e.technical, "TypeError: boom at line 4"); // it goes in the collapsed technical note
});

test("the date question reads naturally in both orders", () => {
  const q = dateOrderQuestion({ data: { sample: [3, 4, 24] } });
  assert.equal(q.text, "Is 03/04/24 the 3rd of April or March 4th?");
  assert.equal(q.dmy, "3rd of April");
  assert.equal(q.mdy, "March 4th");
  assert.equal(dateOrderQuestion({ data: {} }), null);
});

test("ordinals", () => {
  assert.deepEqual([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 31].map(ordinal), ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "31st"]);
});
