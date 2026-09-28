import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Browser tests exercise our local API, not external CDN availability.
  await page.route("https://st.max.ru/**", (route) => route.abort());
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
});

test("personal route: goals, reminder action, persistence and deletion", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Найди свою олимпиаду" }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("catalog.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Собрать маршрут" }).click();
  const modal = page.getByRole("dialog");
  await expect(modal).toBeVisible();
  await modal.getByLabel(/Прикладная математика и информатика/).check();
  await modal.getByRole("switch").check();
  await modal.getByLabel("Разрешаю сохранять").check();
  await modal.getByRole("button", { name: "Сохранить мой маршрут" }).click();
  await expect(modal).not.toBeVisible();
  await page
    .getByRole("button", {
      name: "Добавить в маршрут: Всероссийская олимпиада школьников, Математика",
      exact: true,
    })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой маршрут" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Математика", exact: true }),
  ).toBeVisible();
  await page.getByText("Проверить напоминания · тестовые события").click();
  await page
    .getByRole("button", { name: "Тест регистрации", exact: true })
    .click();
  await expect(
    page.getByText("Пример в браузере", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Я зарегистрировался", exact: true })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой маршрут" })
    .click();
  await expect(
    page.getByLabel("Статус: Всероссийская олимпиада школьников, Математика"),
  ).toHaveValue("registered");
  await page.reload();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой маршрут" })
    .click();
  await expect(
    page.getByLabel("Статус: Всероссийская олимпиада школьников, Математика"),
  ).toHaveValue("registered");
  await page.screenshot({
    path: testInfo.outputPath("route.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой профиль" })
    .click();
  await page
    .getByRole("button", { name: "Удалить профиль", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Удалить", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Собрать маршрут" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("catalog filtering and honest rules in the detail dialog", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Информатика", exact: true }).click();
  await expect(page.locator(".olympiad-card")).toHaveCount(3);
  await page
    .getByRole("textbox", { name: "Поиск олимпиад" })
    .fill("нет такой олимпиады");
  await expect(
    page.getByText("По этим условиям ничего не нашли"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Сбросить фильтры" }).click();
  await expect(page.locator(".olympiad-card")).toHaveCount(5);
  await page
    .locator(".olympiad-card")
    .filter({ hasText: "Высшая проба" })
    .first()
    .getByRole("button", { name: "Условия и сроки" })
    .click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByText("Нужна проверка", { exact: true })).toHaveCount(
    2,
  );
  await expect(modal.getByText(/Они не подтверждают льготу/)).toBeVisible();
  await modal.getByRole("button", { name: "Закрыть", exact: true }).click();
  await expect(modal).not.toBeVisible();
});
