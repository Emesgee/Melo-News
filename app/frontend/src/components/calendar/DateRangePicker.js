// DateRangePicker.js
import React from "react";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";

const DateRangePicker = ({ fromDate, toDate, onFromChange, onToChange }) => {
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <div className="date-fields">
      <DatePicker
        label="From Date"
        value={fromDate}
        onChange={onFromChange}
        slotProps={{
            popper: {
            disablePortal: false,  // ✅ ensures popup attaches to body
            modifiers: [
                {
                name: "zIndex",
                enabled: true,
                phase: "write",
                fn: ({ state }) => {
                    state.styles.popper.zIndex = 20000; // keep above overlay
                }
                }
            ]
            }
        }}
        />

        <DatePicker
        label="To Date"
        value={toDate}
        onChange={onToChange}
        slotProps={{
            popper: {
            disablePortal: false,
            modifiers: [
                {
                name: "zIndex",
                enabled: true,
                phase: "write",
                fn: ({ state }) => {
                    state.styles.popper.zIndex = 20000;
                }
                }
            ]
            }
        }}
        />

      </div>
    </LocalizationProvider>
  );
};

export default DateRangePicker;
