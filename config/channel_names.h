#pragma once

// 0: имена из языкового каталога; 1: свои имена из таблицы ниже.
#ifndef USE_CUSTOM_CHANNEL_NAMES
#define USE_CUSTOM_CHANNEL_NAMES 0
#endif
#if USE_CUSTOM_CHANNEL_NAMES

// Названия 14 независимых каналов.
static const wchar_t *relayNames[] = {
  L"Pump 1",
  L"Pump 2",
  L"Pump 3",
  L"Pump 4",
  L"Pump 5",
  L"Pump 6",
  L"Pump 7",
  L"Pump 8",
  L"Pump 9",
  L"Pump 10",
  L"Pump 11",
  L"Pump 12",
  L"Pump 13",
  L"Pump 14",
};


#endif
