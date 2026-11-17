select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with child as (
    select fk_date as from_field
    from "healthdata_dw"."dw_gold"."fact_hospital_beds"
    where fk_date is not null
),

parent as (
    select sk_date as to_field
    from "healthdata_dw"."dw_gold"."dim_date"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



      
    ) dbt_internal_test