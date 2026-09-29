import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Browser tests exercise our local API, not external CDN availability.
  await page.route("https://st.max.ru/**", (route) => route.abort());
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
});

test("personal route: derived year, status, persistence and deletion", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Олимпиады", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("catalog.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Настроить навигатор" }).click();
  await page.getByRole("button", { name: "Принимаю", exact: true }).click();
  const modal = page.getByRole("dialog");
  await expect(modal).toBeVisible();
  await modal
    .getByRole("checkbox", {
      name: "НИУ ВШЭ, Прикладная математика и информатика",
      exact: true,
    })
    .check();
  await modal.getByLabel("Сейчас учусь в").selectOption("11");
  const year = new Date().getFullYear() + (new Date().getMonth() >= 8 ? 1 : 0);
  await expect(modal.getByLabel("Год поступления")).toHaveValue(String(year));
  await expect(modal.getByLabel("Год поступления")).toHaveAttribute(
    "readonly",
    "",
  );
  await modal.getByLabel("Сейчас учусь в").selectOption("9");
  await expect(modal.getByLabel("Год поступления")).toHaveValue(
    String(year + 2),
  );
  await expect(
    page.getByRole("button", { name: "Напоминания", exact: true }),
  ).toHaveCount(0);
  await expect(modal.getByText("После окончания 11 класса")).toHaveCount(0);
  await modal.getByRole("button", { name: "Сохранить" }).click();
  await expect(modal).not.toBeVisible();
  await page
    .getByRole("button", {
      name: "Добавить в маршрут: Всероссийская олимпиада школьников, Математика",
      exact: true,
    })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой навигатор" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Математика", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Статус: Всероссийская олимпиада школьников, Математика")
    .selectOption("registered");
  await expect(
    page.getByLabel("Статус: Всероссийская олимпиада школьников, Математика"),
  ).toHaveValue("registered");
  await page.reload();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой навигатор" })
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
    page.getByRole("button", { name: "Настроить навигатор" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("catalog filtering and honest rules in the detail dialog", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Предмет олимпиады").selectOption("informatics");
  await expect(page.locator(".olympiad-card")).toHaveCount(4);
  await page
    .getByRole("textbox", { name: "Поиск олимпиад" })
    .fill("нет такой олимпиады");
  await expect(
    page.getByText("По этим условиям ничего не нашли"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Сбросить фильтры" }).click();
  await expect(page.locator(".olympiad-card")).toHaveCount(19);
  await page
    .locator(".olympiad-card")
    .filter({ hasText: "Высшая проба" })
    .first()
    .getByRole("button", { name: "Условия и сроки" })
    .click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByText("Нужна проверка", { exact: true })).toHaveCount(
    4,
  );
  await expect(modal.getByText(/Данные актуальны на/)).toBeVisible();
  await modal.getByRole("button", { name: "Закрыть", exact: true }).click();
  await expect(modal).not.toBeVisible();
});

test("program picker scales to 100 programs and preserves selection across filters", async ({
  page,
  request,
}, testInfo) => {
  const catalog = await (await request.get("/api/v1/catalog")).json();
  catalog.programs = Array.from({ length: 100 }, (_, i) => ({
    ...catalog.programs[i % 4],
    id: `test-${i}`,
    name: `Программа ${String(i).padStart(3, "0")}`,
    short_name: `П${i}`,
  }));
  await page.route("**/api/v1/catalog", (r) => r.fulfill({ json: catalog }));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Настроить навигатор", exact: true })
    .click();
  await page.getByRole("button", { name: "Принимаю", exact: true }).click();
  const modal = page.getByRole("dialog");
  await expect(modal.locator(".program-option")).toHaveCount(12);
  await page.screenshot({ path: testInfo.outputPath("profile-top.png") });
  await modal.getByLabel("Город", { exact: true }).selectOption("Москва");
  await expect(
    modal.getByText("Найдено программ: 50", { exact: true }),
  ).toBeVisible();
  await modal
    .getByLabel("Направление", { exact: true })
    .selectOption("09.03.04 Программная инженерия");
  await expect(
    modal.getByText("Найдено программ: 25", { exact: true }),
  ).toBeVisible();
  await modal.getByLabel("Поиск программы", { exact: true }).fill("001");
  await expect(modal.locator(".program-option")).toHaveCount(1);
  await modal.getByLabel(/Программа 001/).check();
  await modal.getByRole("button", { name: "Сбросить", exact: true }).click();
  await modal.getByRole("button", { name: "Далее", exact: true }).click();
  await expect(
    modal.getByRole("button", { name: "Убрать цель: Программа 001" }),
  ).toBeVisible();
  await modal.getByText("Выбрать предметы", { exact: false }).click();
  await modal.getByLabel("Поиск предметов").fill("Химия");
  await modal.getByLabel("Химия", { exact: true }).check();
  await expect(
    modal.getByRole("button", { name: "Убрать предмет: Химия" }),
  ).toBeVisible();
  await expect(
    modal.getByText("Разрешаю сохранять", { exact: false }),
  ).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("profile-100.png") });
  expect(await modal.evaluate((e) => e.scrollWidth <= e.clientWidth)).toBe(
    true,
  );
});

test("chat button returns to MAX using the bridge", async ({
  page,
  request,
}) => {
  const login = await (await request.post("/api/v1/auth/demo")).json();
  await page.addInitScript(() => {
    Object.assign(window, {
      bridgeClosed: 0,
      WebApp: {
        initData: "bridge-test",
        ready: () => {},
        close: () => {
          const w = window as unknown as { bridgeClosed: number };
          w.bridgeClosed += 1;
        },
        openLink: () => {
          throw new Error("External link must not be used for chat");
        },
      },
    });
  });
  await page.route("**/api/v1/auth/max", (r) => r.fulfill({ json: login }));
  await page.route("**/api/v1/catalog", async (r) => {
    const data = await (await r.fetch()).json();
    await r.fulfill({
      json: { ...data, bot_url: "https://max.ru/t529_hakaton_max_bot" },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Принимаю", exact: true }).click();
  await page.getByRole("button", { name: "Открыть чат" }).click();
  expect(
    await page.evaluate(
      () => (window as unknown as { bridgeClosed: number }).bridgeClosed,
    ),
  ).toBe(1);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Мой профиль" })
    .click();
  await expect(
    page.getByRole("button", { name: "Принимаю", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Сохранить", exact: true }),
  ).toBeVisible();
  await request.delete("/api/v1/me", {
    headers: { Authorization: `Bearer ${login.token}` },
  });
});

test("chat button navigates directly in a browser", async ({ page }) => {
  await page.route("**/api/v1/catalog", async (r) => {
    const data = await (await r.fetch()).json();
    await r.fulfill({
      json: { ...data, bot_url: "https://max.ru/t529_hakaton_max_bot" },
    });
  });
  await page.route("https://max.ru/t529_hakaton_max_bot", (r) =>
    r.fulfill({ contentType: "text/html", body: "Bot page" }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Открыть чат" }).click();
  await expect(page).toHaveURL("https://max.ru/t529_hakaton_max_bot");
});
