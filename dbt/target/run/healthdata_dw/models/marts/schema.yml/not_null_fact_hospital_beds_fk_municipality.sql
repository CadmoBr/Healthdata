select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select fk_municipality
from "healthdata_dw"."dw_gold"."fact_hospital_beds"
where fk_municipality is null



      
    ) dbt_internal_test